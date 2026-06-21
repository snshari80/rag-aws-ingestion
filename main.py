from app.worker.sqs_worker import SQSWorker
from dotenv import load_dotenv
load_dotenv()

from app.core.config import (SQS_QUEUE_URL, SQS_DLQ_URL)
from app.core.logger import logger

def main():
    if not SQS_QUEUE_URL and not SQS_DLQ_URL:
        logger.error("Please set both SQS_QUEUE_URL and SQS_DLQ_URL")
        raise ValueError("Please set both SQS_QUEUE_URL and SQS_DLQ_URL")
    
    worker = SQSWorker()
    worker.run()

if __name__ == "__main__":
    main()