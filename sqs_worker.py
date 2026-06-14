import logging
import sys
import boto3
import json
import time
import urllib.parse
from config import (
    SQS_QUEUE_URL,
    SQS_BATCH_SIZE,
    SQS_WAIT_SECONDS,
    SQS_VISIBILITY_TIMEOUT,
    WORKER_CONCURRENCY,
    AWS_REGION,
)
from ingestion_pipeline import IngestionPipline
import threading

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    stream=sys.stdout,
)

logger = logging.getLogger(__name__)

class SQSWorker:
    def __init__(self):
        if not SQS_QUEUE_URL:
            raise ValueError("SQS QUEUE URL is not available. Please set it")
        self.sqs = boto3.client("sqs",AWS_REGION)
        self._status   = {"processed": 0, "skipped": 0, "failed": 0}
        self.ingest = IngestionPipline()

        logger.info(f"SQS Worker ready — queue={SQS_QUEUE_URL}")
        logger.info(f"  concurrency={WORKER_CONCURRENCY}, batch={SQS_BATCH_SIZE}, "
                    f"visibility_timeout={SQS_VISIBILITY_TIMEOUT}s")
        

    def run(self):
        logger.info(f"Worker Loop started - waiting for messages")
        try:
            messages = self.poll()
            print(messages)
            if not messages:
                logger.debug("Queue empty — polling again...")

            logger.info(f"Received {len(messages)} message(s)")

            if WORKER_CONCURRENCY == 1:
                for msg in messages:
                    self._handle_message(msg)
            else:
                threads = [threading.Thread(target=self._handle_message, args=(msg)) for msg in messages]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join()
        
        except Exception as e:
            logger.error(f"Error has occured with worker thread {e}")
            time.sleep(5)

    def poll(self)-> list:
        response = self.sqs.receive_message(
            QueueUrl= SQS_QUEUE_URL,
            MaxNumberOfMessages = SQS_BATCH_SIZE,
            WaitTimeSeconds     = SQS_WAIT_SECONDS,
            VisibilityTimeout   = SQS_VISIBILITY_TIMEOUT,
            AttributeNames      = ["ApproximateReceiveCount"],
        )
        return response.get("Messages", [])

    def _handle_message(self,message:dict):
        message_id = message.get("MessageId", "Unknown")
        receive_count = message.get("Attributes",{}).get("ApproximateReceiveCount" , 1)

        logger.info(f"[MSG :{message_id[:8]} Processing (attempt: {receive_count})]")
        bucket, key = self._parse_message(message)
        self.ingest.ingest(bucket,key)


    def _parse_message(self, message:dict):
        message_id = message.get("MessageId", "Unknown")
        body = json.loads(message.get("Body",{}))
        records = body.get("Records",[])
        if not records:
            logger.info(f"No Records found on this message id: {message_id}")
            raise ValueError (f"No Records found on this S3")
        
        event_name = records[0]["eventName"]
        if event_name != "ObjectCreated:Put":
            logger.info(f"Event is not from S3 Upload: {message_id}")
            raise ValueError (f"Event is not from S3 Upload")
        
        s3_info = records[0].get("s3" , {})
        bucket_name = s3_info.get("bucket" , {}).get("name","")
        raw_key = s3_info.get("object" , {}).get("key","")
        key = urllib.parse.unquote_plus(raw_key)

        if not bucket_name or not key:
            raise ValueError(f"No bucket name and key for this S3 event: Bucket={bucket_name} Key={key}")

        return bucket_name, key

if __name__ == "__main__":
    logger.info("*" *73)
    logger.info("RAG Ingestion Worker")
    logger.info("=" *73)
    logger.info(f"  SQS Queue  : {SQS_QUEUE_URL or 'NOT SET'}")
    logger.info(f"  Concurrency: {WORKER_CONCURRENCY}")
    logger.info(f"  Region     : {AWS_REGION}")
    logger.info("=" * 55)
    worker = SQSWorker()
    worker.run()