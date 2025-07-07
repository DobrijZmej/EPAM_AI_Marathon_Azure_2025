import logging
import azure.functions as func
import asyncio
from .analyze_sentiment_core import analyze_and_update_sentiment

# Set up a custom logger with module and function name in format
logging.basicConfig(
    format='[%(asctime)s] [%(levelname)s] [%(module)s.%(funcName)s] %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main(req: func.HttpRequest) -> func.HttpResponse:
    logger.info('Sentiment analysis HTTP function started.')
    try:
        max_items = int(req.params.get('max_items', 100))
    except Exception:
        max_items = 100
    result = asyncio.run(analyze_and_update_sentiment(max_items=max_items))
    logger.info(f'Sentiment analysis result: {result}')
    return func.HttpResponse(str(result), mimetype="application/json")
