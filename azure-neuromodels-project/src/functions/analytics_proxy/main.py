import os
import json
import logging
import azure.functions as func
import asyncio
from azure.kusto.data import KustoClient, KustoConnectionStringBuilder
from azure.kusto.data.exceptions import KustoApiError


# Kusto (Azure Data Explorer) connection settings
KUSTO_CLUSTER = os.environ.get("KUSTO_CLUSTER")  # e.g. "https://<cluster>.kusto.windows.net"
KUSTO_DB = os.environ.get("KUSTO_DB")
KUSTO_CLIENT_ID = os.environ.get("KUSTO_CLIENT_ID")
KUSTO_CLIENT_SECRET = os.environ.get("KUSTO_CLIENT_SECRET")
KUSTO_TENANT_ID = os.environ.get("KUSTO_TENANT_ID")


def get_kusto_client():
    # For hackathon: use client id/secret, but for prod use managed identity
    kcsb = KustoConnectionStringBuilder.with_aad_application_key_authentication(
        KUSTO_CLUSTER, KUSTO_CLIENT_ID, KUSTO_CLIENT_SECRET, KUSTO_TENANT_ID
    )
    return KustoClient(kcsb)

def build_kusto_query(metric):
    # Map metric to Kusto query
    if metric == "sentiment":
        # Pie: розподіл sentiment
        return "DialogMetrics | where metric == 'sentiment' | summarize value=count() by label=value"
    elif metric == "sentiment_time":
        # Timechart: sentiment by hour and label (всі комбінації, label як string)
        return (
            "let hours = range hour from toscalar(DialogMetrics | where metric == 'sentiment' | summarize min(bin(TimeGenerated, 1h))) "
            "to toscalar(DialogMetrics | where metric == 'sentiment' | summarize max(bin(TimeGenerated, 1h))) step 1h;\n"
            "let labels = toscalar(DialogMetrics | where metric == 'sentiment' | summarize make_list(tostring(value)));\n"
            "hours\n"
            "| mv-expand label = labels\n"
            "| extend label = tostring(label)\n"
            "| join kind=leftouter (\n"
            "    DialogMetrics | where metric == 'sentiment' | extend label = tostring(value) | summarize value=count() by hour=bin(TimeGenerated, 1h), label\n"
            ") on hour, label\n"
            "| project hour, label, value=coalesce(value, 0)\n"
            "| order by hour asc, label asc"
        )
    elif metric == "languages":
        # Pie: розподіл мов
        return "DialogMetrics | where metric == 'language' | summarize value=count() by label=value"
    elif metric == "top_phrases":
        # Wordcloud: топ-20 ключових слів
        return "DialogMetrics | where metric == 'keyword' | summarize value=count() by label=tostring(value) | top 20 by value desc"
    elif metric == "top_users":
        # Column: топ користувачів
        return "DialogMetrics | summarize value=count() by label=user_id | top 10 by value desc"
    else:
        return None

def query_kusto(metric):
    client = get_kusto_client()
    query = build_kusto_query(metric)
    if not query:
        logging.warning(f"[AnalyticsProxy] Unknown metric: {metric}")
        return []
    try:
        response = client.execute(KUSTO_DB, query)
        rows = response.primary_results[0]
        result = []
        for row in rows:
            # Для sentiment_time повертаємо hour, label, value
            if metric == "sentiment_time":
                result.append({
                    "hour": str(row["hour"]),
                    "label": row["label"],
                    "value": row["value"]
                })
            else:
                # Each row: label, value
                result.append({"label": row["label"], "value": row["value"]})
        logging.info(f"[AnalyticsProxy] Kusto returned {len(result)} rows for metric {metric}")
        return result
    except KustoApiError as e:
        logging.error(f"[AnalyticsProxy] Kusto error: {e}")
        return {"error": f"KustoApiError: {str(e)}"}
    except Exception as e:
        logging.error(f"[AnalyticsProxy] Unexpected error: {e}")
        return {"error": f"Exception: {str(e)}"}


def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        logging.info("[AnalyticsProxy] Function triggered for dashboard analytics.")
        # Діагностика: логування змінних оточення
        logging.info(f"KUSTO_CLUSTER={KUSTO_CLUSTER}")
        logging.info(f"KUSTO_DB={KUSTO_DB}")
        logging.info(f"KUSTO_CLIENT_ID={KUSTO_CLIENT_ID}")
        logging.info(f"KUSTO_CLIENT_SECRET={'set' if KUSTO_CLIENT_SECRET else 'empty'}")
        logging.info(f"KUSTO_TENANT_ID={KUSTO_TENANT_ID}")

        # Get metric from query string
        metric = req.params.get("metric")
        if not metric:
            return func.HttpResponse(
                json.dumps({"error": "Missing 'metric' parameter"}),
                mimetype="application/json",
                status_code=400,
                headers={"Access-Control-Allow-Origin": "*"}
            )
        result = query_kusto(metric)
        # Якщо сталася помилка — повертаємо 500 і текст помилки
        if isinstance(result, dict) and "error" in result:
            return func.HttpResponse(
                json.dumps(result),
                mimetype="application/json",
                status_code=500,
                headers={"Access-Control-Allow-Origin": "*"}
            )
        return func.HttpResponse(
            json.dumps(result),
            mimetype="application/json",
            status_code=200,
            headers={"Access-Control-Allow-Origin": "*"}
        )
    except Exception as e:
        logging.error(f"[AnalyticsProxy] FATAL: {e}")
        return func.HttpResponse(
            json.dumps({"error": f"FATAL: {str(e)}"}),
            mimetype="application/json",
            status_code=500,
            headers={"Access-Control-Allow-Origin": "*"}
        )
