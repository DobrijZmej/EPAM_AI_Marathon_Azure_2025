import os
import logging
import azure.functions as func
import requests
import json
from typing import List
import openai
import uuid
import asyncio
import traceback
from azure.cosmos.aio import CosmosClient
from azure.cosmos.exceptions import CosmosResourceExistsError, CosmosHttpResponseError

async def get_last_user_history(user_id: str, limit: int = 5):
    """
    Повертає останні 5 пар (question, answer) для user_id, впорядковані за часом.
    """
    try:
        endpoint = os.environ.get("COSMOSDB_ENDPOINT")
        key = os.environ.get("COSMOSDB_KEY")
        database_name = os.environ.get("COSMOSDB_DATABASE")
        container_name = os.environ.get("COSMOSDB_CONTAINER")
        if not all([endpoint, key, database_name, container_name]):
            return []
        async with CosmosClient(endpoint, key) as client:
            db = client.get_database_client(database_name)
            container = db.get_container_client(container_name)
            # Вибираємо останні 50 подій для user_id (щоб знайти пари question-answer)
            query = f"SELECT * FROM c WHERE c.user_id=@user_id AND (c.step='question' OR c.step='answer') ORDER BY c._ts DESC"
            params = [{"name": "@user_id", "value": user_id}]
            items = [item async for item in container.query_items(query, parameters=params)]
            # Сортуємо за часом, групуємо по dialog_id, але дозволяємо брати пари з різних dialog_id
            questions = [i for i in items if i.get("step") == "question"]
            answers = [i for i in items if i.get("step") == "answer"]
            # Беремо останні N питань і для кожного шукаємо найближчу відповідь за dialog_id
            history = []
            for q in questions:
                # Знаходимо відповідь з таким же dialog_id
                a = next((a for a in answers if a.get("dialog_id") == q.get("dialog_id")), None)
                if a:
                    history.append((q["content"], a["content"]))
                if len(history) >= limit:
                    break
            return history
    except Exception as e:
        logging.error(f"[CosmosDB] Failed to get user history: {e}")
        return []

async def save_event(event: dict):
    """
    Асинхронно зберігає подію у Cosmos DB. Fail-safe: логування помилок, не кидає виключення.
    Автоматично генерує id, якщо не вказано.
    """
    try:
        endpoint = os.environ.get("COSMOSDB_ENDPOINT")
        key = os.environ.get("COSMOSDB_KEY")
        database_name = os.environ.get("COSMOSDB_DATABASE")
        container_name = os.environ.get("COSMOSDB_CONTAINER")
        logging.info(f"[CosmosDB] endpoint={endpoint}, key={'set' if key else 'MISSING'}, db={database_name}, container={container_name}")
        if not all([endpoint, key, database_name, container_name]):
            logging.error(f"[CosmosDB] One or more Cosmos DB environment variables are missing!")
            return
        if "id" not in event:
            event["id"] = str(uuid.uuid4())
        logging.info(f"[CosmosDB] Saving event: {json.dumps(event, ensure_ascii=False)[:500]}")
        async with CosmosClient(endpoint, key) as client:
            db = client.get_database_client(database_name)
            container = db.get_container_client(container_name)
            await container.create_item(event)
        logging.info("[CosmosDB] Event saved successfully.")
    except Exception as e:
        logging.error(f"[CosmosDB] Failed to save event: {e}")
        logging.error(traceback.format_exc())
        # Fail-safe: не кидаємо далі

def get_search_results(question: str, previous_qa: str = "") -> dict:
    """
    Виконує пошук у базі знань. Якщо передано previous_qa, додає його до пошукового запиту.
    """
    endpoint = os.environ["SEARCH_SERVICE_ENDPOINT"]
    api_key = os.environ["SEARCH_API_KEY"]
    index_name = os.environ["SEARCH_INDEX_NAME"]
    url = f"{endpoint}/indexes/{index_name}/docs/search?api-version=2023-07-01-Preview"
    headers = {
        "Content-Type": "application/json",
        "api-key": api_key
    }
    if previous_qa:
        search_query = f"Previous dialog: {previous_qa}. Current question: {question}"
    else:
        search_query = question
    payload = {
        "search": search_query,
        "top": 3
    }
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()

def ask_llm(question: str, user_history: str = "", kb_context: str = "") -> str:
    """
    Формує промпт для LLM з окремих компонентів: історія діалогів, знання, питання.
    user_history: стисла історія діалогів (може бути порожньою)
    kb_context: релевантні знання з бази (може бути порожнім)
    """
    client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    prompt = (
        "You are Servantus, a helpful assistant at the 'CoolAir Air Conditioner Store'.\n"
        "Always use both the provided knowledge base and the dialog history to answer the customer's question as helpfully and contextually as possible.\n"
        "If the dialog history contains relevant information, you must use it in your answer. If the knowledge base contains relevant information, you must use it in your answer.\n"
        "If neither the dialog history nor the knowledge base are relevant to the question, politely redirect the conversation to topics related to air conditioners, climate, or store services.\n"
        "Respond in the same language as the question.\n\n"
    )
    if user_history:
        prompt += "[Dialog history]\n" + user_history.strip() + "\n\n"
    if kb_context:
        prompt += "[Knowledge base]\n" + kb_context.strip() + "\n\n"
    prompt += f"Customer question: {question}\nServantus's answer:"
    logging.info(f"[LLM prompt] {prompt}...")
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=256,
        temperature=0.2,
    )
    return response.choices[0].message.content.strip()

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    try:
        req_body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            "Invalid JSON.", status_code=400
        )
    user_id = req_body.get("user_id")
    question = req_body.get("question")
    if not user_id or not question:
        return func.HttpResponse(
            "Missing 'user_id' or 'question' in request.", status_code=400
        )
    try:
        import datetime
        dialog_id = req_body.get("dialog_id") or str(uuid.uuid4())
        # 1. Зберігаємо подію question
        event_question = {
            "dialog_id": dialog_id,
            "step": "question",
            "user_id": user_id,
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "content": question,
            "meta": {
                "lang": req_body.get("lang", "uk"),
                "source": None,
                "score": None,
                "latency_ms": None
            }
        }
        logging.info("[CosmosDB] Calling save_event for question...")
        asyncio.run(save_event(event_question))

        # 2. Додаємо історію користувача до контексту
        user_history = asyncio.run(get_last_user_history(user_id, limit=5))
        history_text = ""
        previous_qa = ""
        if user_history:
            history_text = "\n\n---\n\n".join([
                f"User: {q}\nServantus: {a}" for q, a in reversed(user_history)
            ])
            # Беремо останню пару (question, answer) для пошукового запиту
            last_qa = user_history[-1]  # (q, a)
            previous_qa = f"{last_qa[0]} {last_qa[1]}"

        # 3. Пошук у базі знань з урахуванням попереднього діалогу
        search_results = get_search_results(question, previous_qa=previous_qa)
        docs = search_results.get("value", [])
        if not docs:
            return func.HttpResponse(
                json.dumps({
                    "answer": "Нічого не знайдено.",
                    "source_documents": [],
                    "search_snippet": ""
                }),
                mimetype="application/json"
            )
        # Вибираємо всі документи з score >= 80% від максимального
        max_score = max(doc.get("@search.score", 0) for doc in docs)
        threshold = max_score * 0.8
        relevant_docs = [doc for doc in docs if doc.get("@search.score", 0) >= threshold]

        # 4. Зберігаємо події search_result для кожного документа
        for doc in relevant_docs:
            event_search = {
                "dialog_id": dialog_id,
                "step": "search_result",
                "user_id": user_id,
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                "content": doc.get("content", ""),
                "meta": {
                    "lang": req_body.get("lang", "uk"),
                    "source": doc.get("source") or doc.get("metadata_storage_path"),
                    "score": doc.get("@search.score"),
                    "latency_ms": None
                }
            }
            logging.info("[CosmosDB] Calling save_event for search_result...")
            asyncio.run(save_event(event_search))

        # 5. Формуємо компоненти для промпта
        kb_context = "\n\n---\n\n".join(doc.get("content", "") for doc in relevant_docs)
        source_urls = [doc.get("source", "") or doc.get("metadata_storage_path", "") for doc in relevant_docs if doc.get("source", "") or doc.get("metadata_storage_path", "")]
        snippet = kb_context

        user_answer = ask_llm(question, user_history=history_text, kb_context=kb_context)

        # 6. Зберігаємо подію answer
        event_answer = {
            "dialog_id": dialog_id,
            "step": "answer",
            "user_id": user_id,
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "content": user_answer,
            "meta": {
                "lang": req_body.get("lang", "uk"),
                "source": None,
                "score": None,
                "latency_ms": None
            }
        }
        logging.info("[CosmosDB] Calling save_event for answer...")
        asyncio.run(save_event(event_answer))

        return func.HttpResponse(
            json.dumps({
                "answer": user_answer,
                "source_documents": source_urls,
                "search_snippet": snippet
            }),
            mimetype="application/json"
        )
    except Exception as e:
        logging.error(f"Error: {e}")
        return func.HttpResponse(
            f"Error: {str(e)}", status_code=500
        )
