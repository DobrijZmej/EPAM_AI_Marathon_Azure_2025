import os
import logging
from azure.cosmos.aio import CosmosClient
from azure.ai.textanalytics.aio import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential
import asyncio
import traceback

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
            # Prepare batch for Text Analytics
            # Step 1: Detect language for items where meta.lang is missing or set to 'uk' (default)
            credential = AzureKeyCredential(TEXT_ANALYTICS_KEY)
            async with TextAnalyticsClient(TEXT_ANALYTICS_ENDPOINT, credential) as ta_client:
                # Detect language in batches
                batch_size = 10
                for i in range(0, len(items), batch_size):
                    batch_items = items[i:i+batch_size]
                    detect_docs = []
                    detect_indices = []
                    for idx, item in enumerate(batch_items):
                        lang = item.get("meta", {}).get("lang")
                        # Detect if lang is missing or set to 'en' (default)
                        if not lang or lang == "en":
                            detect_docs.append({"id": item["id"], "text": item["content"]})
                            detect_indices.append(idx)
                    if detect_docs:
                        try:
                            detect_results = await ta_client.detect_language(documents=detect_docs)
                            for res, idx in zip(detect_results, detect_indices):
                                if not res.is_error:
                                    detected_lang = res.primary_language.iso6391_name
                                    # Set detected language in meta
                                    if "meta" not in batch_items[idx] or not isinstance(batch_items[idx]["meta"], dict):
                                        batch_items[idx]["meta"] = {}
                                    batch_items[idx]["meta"]["lang"] = detected_lang
                                    logger.info(f"[LangDetect] id={batch_items[idx]['id']} detected lang={detected_lang}")
                                else:
                                    logger.warning(f"[LangDetect] Error for id={batch_items[idx]['id']}: {res.error}")
                        except Exception as e:
                            logger.error(f"[LangDetect] Exception in batch: {e}\n{traceback.format_exc()}")

            # Step 2: Prepare documents for sentiment analysis (now with detected language)
            documents = [
                {"id": item["id"], "text": item["content"], "language": item.get("meta", {}).get("lang", "uk")}
                for item in items
            ]
            logger.info(f"[Sentiment] Documents to analyze: {[d['id'] for d in documents]}")
            processed_count = 0
            async with TextAnalyticsClient(TEXT_ANALYTICS_ENDPOINT, credential) as ta_client:
                # Batch processing: max 10 documents per request
                batch_size = 10
                for i in range(0, len(documents), batch_size):
                    batch_docs = documents[i:i+batch_size]
                    batch_items = items[i:i+batch_size]
                    logger.info(f"[Sentiment] Sending batch: {[d['id'] for d in batch_docs]}")
                    try:
                        response = await ta_client.analyze_sentiment(documents=batch_docs)
                    except Exception as e:
                        logger.error(f"[Sentiment] Exception in batch: {e}\n{traceback.format_exc()}")
                        continue
                    for doc_result, item in zip(response, batch_items):
                        logger.info(f"[Sentiment] Processing item id={item['id']}")
                        logger.info(f"[Sentiment] Raw item: {item}")
                        # Ensure meta exists and is a dict
                        if "meta" not in item or not isinstance(item["meta"], dict):
                            logger.warning(f"[Sentiment] Item id={item['id']} has no 'meta' field or it's not a dict. Creating empty meta.")
                            item["meta"] = {}
                        if not doc_result.is_error:
                            sentiment = doc_result.sentiment
                            scores = doc_result.confidence_scores
                            logger.info(f"[Sentiment] id={item['id']} sentiment={sentiment} scores={{'positive': {scores.positive}, 'neutral': {scores.neutral}, 'negative': {scores.negative}}}")
                            item["meta"]["sentiment"] = sentiment
                            item["meta"]["sentiment_score"] = {
                                "positive": scores.positive,
                                "neutral": scores.neutral,
                                "negative": scores.negative
                            }
                            try:
                                result = await container.replace_item(item=item["id"], body=item)
                                logger.info(f"[CosmosDB] Updated item id={item['id']}, result: {result}")
                                processed_count += 1
                            except Exception as e:
                                logger.error(f"[CosmosDB] Failed to update item {item['id']}: {e}\n{traceback.format_exc()}")
                        else:
                            logger.error(f"[TextAnalytics] Error for item {item['id']}: {doc_result.error}")
            logger.info(f"[Sentiment] Processed {processed_count} items.")
            return {"processed": processed_count}
    except Exception as e:
        logger.error(f"[Sentiment] Exception: {e}\n{traceback.format_exc()}")
        return {"error": str(e)}
