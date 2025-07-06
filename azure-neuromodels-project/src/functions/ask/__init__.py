import os
import logging
import azure.functions as func
import requests
import json
from typing import List
import openai

def get_search_results(question: str) -> dict:
    endpoint = os.environ["SEARCH_SERVICE_ENDPOINT"]
    api_key = os.environ["SEARCH_API_KEY"]
    index_name = os.environ["SEARCH_INDEX_NAME"]
    url = f"{endpoint}/indexes/{index_name}/docs/search?api-version=2023-07-01-Preview"
    headers = {
        "Content-Type": "application/json",
        "api-key": api_key
    }
    payload = {
        "search": question,
        "top": 3
    }
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()

def ask_llm(question: str, context: str) -> str:
    client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    prompt = (
        "Your name is Servantus. You are a smart, friendly assistant working at the 'CoolAir Air Conditioner Store'. "
        "Your main goal is to answer customer questions as truthfully as possible using only the provided context. "
        "If the question is not related to air conditioners, climate, or the store's services, politely suggest discussing something about the store or its products. "
        "Your second priority is to help the customer reach a purchase decision: if the question is about products, guide the customer toward choosing and buying, and prepare everything for the order if they are ready. "
        "Always respond in the same language as the question.\n\n"
        f"Context:\n{context}\n\n"
        f"Customer question: {question}\n"
        "Servantus's answer:"
    )
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
        search_results = get_search_results(question)
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

        # Об'єднуємо контент
        context = "\n\n---\n\n".join(doc.get("content", "") for doc in relevant_docs)
        source_urls = [doc.get("source", "") or doc.get("metadata_storage_path", "") for doc in relevant_docs if doc.get("source", "") or doc.get("metadata_storage_path", "")]
        snippet = context

        if context.strip():
            user_answer = ask_llm(question, context)
        else:
            user_answer = "На жаль, не вдалося знайти відповідь у базі знань."

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
