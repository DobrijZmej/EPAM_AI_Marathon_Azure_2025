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

def main(mytimer: func.TimerRequest) -> None:
    logger.info('Sentiment analysis timer function started.')
    result = asyncio.run(analyze_and_update_sentiment())
    logger.info(f'Sentiment analysis result: {result}')
