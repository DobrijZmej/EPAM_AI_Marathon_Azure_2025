import os
import logging
import asyncio
import traceback
import requests
import json
import base64
from datetime import datetime
from azure.cosmos.aio import CosmosClient
from azure.ai.textanalytics.aio import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential
from azure.kusto.data import KustoConnectionStringBuilder
from azure.kusto.data.helpers import dataframe_from_result_table
from azure.kusto.ingest import QueuedIngestClient, IngestionProperties
from azure.kusto.ingest.ingestion_properties import DataFormat

# Set up a custom logger with module and function name in format
logging.basicConfig(
    format='[%(asctime)s] [%(levelname)s] [%(module)s.%(funcName)s] %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


COSMOSDB_ENDPOINT = os.environ.get("COSMOSDB_ENDPOINT")
COSMOSDB_KEY = os.environ.get("COSMOSDB_KEY")
COSMOSDB_DATABASE = os.environ.get("COSMOSDB_DATABASE")
COSMOSDB_CONTAINER = os.environ.get("COSMOSDB_CONTAINER")
TEXT_ANALYTICS_ENDPOINT = os.environ.get("TEXT_ANALYTICS_ENDPOINT")
TEXT_ANALYTICS_KEY = os.environ.get("TEXT_ANALYTICS_KEY")
KUSTO_INGEST_URI = os.environ.get("KUSTO_INGEST_URI")
KUSTO_DB = os.environ.get("KUSTO_DB")
KUSTO_TABLE = os.environ.get("KUSTO_TABLE", "DialogMetrics")
KUSTO_INGEST_CLIENT_ID = os.environ.get("KUSTO_INGEST_CLIENT_ID")
KUSTO_INGEST_CLIENT_SECRET = os.environ.get("KUSTO_INGEST_CLIENT_SECRET")
KUSTO_INGEST_TENANT_ID = os.environ.get("KUSTO_INGEST_TENANT_ID")

def build_signature(customer_id, shared_key, date, content_length, method, content_type, resource):
    x_headers = 'x-ms-date:' + date
    string_to_hash = f"{method}\n{str(content_length)}\n{content_type}\n{x_headers}\n{resource}"
    bytes_to_hash = bytes(string_to_hash, encoding="utf-8")
    decoded_key = base64.b64decode(shared_key)
    encoded_hash = base64.b64encode(hmac.new(decoded_key, bytes_to_hash, digestmod=hashlib.sha256).digest()).decode()
    return f"SharedKey {customer_id}:{encoded_hash}"


def ingest_data_to_kusto(records):
    if not (KUSTO_INGEST_URI and KUSTO_DB and KUSTO_TABLE and KUSTO_INGEST_CLIENT_ID and KUSTO_INGEST_CLIENT_SECRET and KUSTO_INGEST_TENANT_ID):
        logger.error("[Kusto] One or more Kusto env variables are missing!")
        return False
    try:
        kcsb = KustoConnectionStringBuilder.with_aad_application_key_authentication(
            KUSTO_INGEST_URI, KUSTO_INGEST_CLIENT_ID, KUSTO_INGEST_CLIENT_SECRET, KUSTO_INGEST_TENANT_ID
        )
        ingest_client = QueuedIngestClient(kcsb)
        # Prepare data as NDJSON
        ndjson = "\n".join(json.dumps(rec, ensure_ascii=False) for rec in records)
        from io import BytesIO
        data_stream = BytesIO(ndjson.encode("utf-8"))
        ingestion_props = IngestionProperties(
            database=KUSTO_DB,
            table=KUSTO_TABLE,
            data_format=DataFormat.JSON,
            flush_immediately=True
        )
        ingest_client.ingest_from_stream(data_stream, ingestion_properties=ingestion_props)
        logger.info(f"[Kusto] Ingested {len(records)} records to {KUSTO_DB}.{KUSTO_TABLE}")
        return True
    except Exception as e:
        logger.error(f"[Kusto] Ingestion failed: {e}\n{traceback.format_exc()}")
        return False

async def analyze_and_update_sentiment(max_items=100):
    if not all([COSMOSDB_ENDPOINT, COSMOSDB_KEY, COSMOSDB_DATABASE, COSMOSDB_CONTAINER, TEXT_ANALYTICS_ENDPOINT, TEXT_ANALYTICS_KEY]):
        logger.error("[Config] One or more environment variables are missing!")
        return {"error": "Missing config"}
    try:
        async with CosmosClient(COSMOSDB_ENDPOINT, COSMOSDB_KEY) as cosmos_client:
            db = cosmos_client.get_database_client(COSMOSDB_DATABASE)
            container = db.get_container_client(COSMOSDB_CONTAINER)
            query = "SELECT * FROM c WHERE (c.step = 'question' OR c.step = 'answer') AND (NOT IS_DEFINED(c.meta.sentiment) OR c.meta.sentiment = null) OFFSET 0 LIMIT @max_items"
            params = [{"name": "@max_items", "value": max_items}]
            items = [item async for item in container.query_items(query, parameters=params)]
            logger.info(f"[Sentiment] Found {len(items)} items to process.")
            if not items:
                logger.info("[Sentiment] No items to process.")
                return {"processed": 0}
            credential = AzureKeyCredential(TEXT_ANALYTICS_KEY)
            # Detect language
            async with TextAnalyticsClient(TEXT_ANALYTICS_ENDPOINT, credential) as ta_client:
                batch_size = 10
                for i in range(0, len(items), batch_size):
                    batch_items = items[i:i+batch_size]
                    detect_docs = []
                    detect_indices = []
                    for idx, item in enumerate(batch_items):
                        lang = item.get("meta", {}).get("lang")
                        if not lang or lang == "en":
                            detect_docs.append({"id": item["id"], "text": item["content"]})
                            detect_indices.append(idx)
                    if detect_docs:
                        try:
                            detect_results = await ta_client.detect_language(documents=detect_docs)
                            for res, idx in zip(detect_results, detect_indices):
                                if not res.is_error:
                                    detected_lang = res.primary_language.iso6391_name
                                    if "meta" not in batch_items[idx] or not isinstance(batch_items[idx]["meta"], dict):
                                        batch_items[idx]["meta"] = {}
                                    batch_items[idx]["meta"]["lang"] = detected_lang
                                    logger.info(f"[LangDetect] id={batch_items[idx]['id']} detected lang={detected_lang}")
                                else:
                                    logger.warning(f"[LangDetect] Error for id={batch_items[idx]['id']}: {res.error}")
                        except Exception as e:
                            logger.error(f"[LangDetect] Exception in batch: {e}\n{traceback.format_exc()}")

            # Після аналізу — оновлюємо документи у Cosmos DB, щоб відмітити як оброблені
            async def update_cosmos_items(container, items):
                for item in items:
                    try:
                        await container.upsert_item(item)
                        logger.info(f"[Cosmos] Updated item id={item['id']} as processed.")
                    except Exception as e:
                        logger.error(f"[Cosmos] Failed to update item id={item['id']}: {e}")

            # Prepare documents for sentiment analysis
            documents = [
                {"id": item["id"], "text": item["content"], "language": item.get("meta", {}).get("lang", "uk")}
                for item in items
            ]
            logger.info(f"[Sentiment] Documents to analyze: {[d['id'] for d in documents]}")
            processed_count = 0
            all_metrics = []
            async with TextAnalyticsClient(TEXT_ANALYTICS_ENDPOINT, credential) as ta_client:
                batch_size = 10
                for i in range(0, len(documents), batch_size):
                    batch_docs = documents[i:i+batch_size]
                    batch_items = items[i:i+batch_size]
                    logger.info(f"[Sentiment] Sending batch: {[d['id'] for d in batch_docs]}")
                    try:
                        sentiment_response = await ta_client.analyze_sentiment(documents=batch_docs)
                    except Exception as e:
                        logger.error(f"[Sentiment] Exception in batch: {e}\n{traceback.format_exc()}")
                        continue
                    try:
                        keyphrases_response = await ta_client.extract_key_phrases(documents=batch_docs)
                    except Exception as e:
                        logger.error(f"[KeyPhrases] Exception in batch: {e}\n{traceback.format_exc()}")
                        keyphrases_response = [None] * len(batch_docs)
                    for doc_result, kp_result, item in zip(sentiment_response, keyphrases_response, batch_items):
                        logger.info(f"[Sentiment] Processing item id={item['id']}")
                        logger.info(f"[Sentiment] Raw item: {item}")
                        # Формуємо записи для Log Analytics
                        dialog_id = item.get("dialog_id") or item.get("id")
                        user_id = item.get("user_id")
                        message_id = item.get("id")
                        message_type = item.get("step")
                        time_generated = item.get("timestamp")
                        if not doc_result.is_error:
                            sentiment = doc_result.sentiment
                            # Оновлюємо CosmosDB: записуємо результат аналізу
                            if "meta" not in item or not isinstance(item["meta"], dict):
                                item["meta"] = {}
                            item["meta"]["sentiment"] = sentiment
                            if hasattr(doc_result, 'detected_language'):
                                item["meta"]["lang"] = doc_result.detected_language.iso6391_name
                            all_metrics.append({
                                "TimeGenerated": time_generated,
                                "metric": "sentiment",
                                "value": sentiment,
                                "message_id": message_id,
                                "user_id": user_id,
                                "dialog_id": dialog_id,
                                "message_type": message_type
                            })
                            all_metrics.append({
                                "TimeGenerated": time_generated,
                                "metric": "language",
                                "value": doc_result.detected_language.iso6391_name if hasattr(doc_result, 'detected_language') else item.get("meta", {}).get("lang", "uk"),
                                "message_id": message_id,
                                "user_id": user_id,
                                "dialog_id": dialog_id,
                                "message_type": message_type
                            })
                        if kp_result and not kp_result.is_error:
                            if "meta" not in item or not isinstance(item["meta"], dict):
                                item["meta"] = {}
                            item["meta"]["key_phrases"] = kp_result.key_phrases
                            for kw in kp_result.key_phrases:
                                all_metrics.append({
                                    "TimeGenerated": time_generated,
                                    "metric": "keyword",
                                    "value": kw,
                                    "message_id": message_id,
                                    "user_id": user_id,
                                    "dialog_id": dialog_id,
                                    "message_type": message_type
                                })
                        processed_count += 1

            # Оновлюємо всі оброблені документи у Cosmos DB
            await update_cosmos_items(container, items)
            # Надсилаємо всі метрики batch-ом у Kusto (Azure Data Explorer)
            if all_metrics:
                logger.info(f"[Kusto] Sending {len(all_metrics)} records to Kusto. Example: {all_metrics[0] if all_metrics else 'EMPTY'}")
                result = ingest_data_to_kusto(all_metrics)
                logger.info(f"[Kusto] ingest_data_to_kusto returned: {result}")
            else:
                logger.warning("[Kusto] all_metrics is empty, nothing to send.")
            logger.info(f"[Sentiment] Processed {processed_count} items.")
            return {"processed": processed_count}
    except Exception as e:
        logger.error(f"[Sentiment] Exception: {e}\n{traceback.format_exc()}")
        return {"error": str(e)}
