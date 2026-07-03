from app.core.logger import logger
import boto3
import json
import time
import urllib.parse
from app.core.config import (
    SQS_QUEUE_URL,
    SQS_BATCH_SIZE,
    SQS_WAIT_SECONDS,
    SQS_VISIBILITY_TIMEOUT,
    WORKER_CONCURRENCY,
    AWS_REGION,
)
from app.pipeline.ingestion_pipeline import IngestionPipline
import threading
 
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
            while True:
                messages = self.poll()
                if not messages:
                    logger.debug("Queue empty — polling again...")
                    continue
 
                logger.info(f"Received {len(messages)} message(s)")
 
                if WORKER_CONCURRENCY == 1:
                    for msg in messages:
                        self._handle_message(msg)
                else:
                    threads = [threading.Thread(target=self._handle_message, args=(msg,)) for msg in messages]
                    for t in threads:
                        t.start()
                    for t in threads:
                        t.join()
               
                logger.info(f"Batch complete — processed={self._status['processed']}, skipped={self._status['skipped']}, failed={self._status['failed']}")
       
        except KeyboardInterrupt:
            logger.info("Worker interrupted by user")
        except Exception as e:
            logger.error(f"Error in worker loop: {e}")
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
 
    def _delete_message(self, receipt_handle:str):
        try:
            self.sqs.delete_message(
                QueueUrl=SQS_QUEUE_URL,
                ReceiptHandle=receipt_handle
            )
        except Exception as e:
            logger.error(f"Failed to delete message: {e}")
 
    def _handle_message(self,message:dict):
        message_id = message.get("MessageId", "Unknown")
        receipt_handle = message.get("ReceiptHandle")
        receive_count = message.get("Attributes",{}).get("ApproximateReceiveCount" , 1)
 
        logger.info(f"[MSG :{message_id[:8]} Processing (attempt: {receive_count})]")
        try:
            bucket, key = self._parse_message(message)
            self.ingest.ingest(bucket,key)
            self._status["processed"] += 1
            logger.info(f"[MSG :{message_id[:8]} SUCCESS]")
        except ValueError as e:
            logger.warning(f"[MSG :{message_id[:8]} SKIPPED] {e}")
            self._status["skipped"] += 1
        except Exception as e:
            logger.error(f"[MSG :{message_id[:8]} FAILED] {e}")
            self._status["failed"] += 1
        finally:
            # Always delete message after processing (success or failure)
            if receipt_handle:
                self._delete_message(receipt_handle)
 
 
    def _parse_message(self, message:dict):
        message_id = message.get("MessageId", "Unknown")
        body = json.loads(message.get("Body",{}))
       
        # Skip S3 test events (sent during SNS subscription confirmation)
        if body.get("Event") == "s3:TestEvent":
            raise ValueError("S3 test event (SNS subscription confirmation)")
       
        records = body.get("Records",[])
        if not records:
            raise ValueError(f"No Records found in message")
       
        event_name = records[0].get("eventName")
        if event_name != "ObjectCreated:Put":
            raise ValueError(f"Event is not S3 upload: {event_name}")
       
        s3_info = records[0].get("s3" , {})
        bucket_name = s3_info.get("bucket" , {}).get("name","")
        raw_key = s3_info.get("object" , {}).get("key","")
        key = urllib.parse.unquote_plus(raw_key)
 
        if not bucket_name or not key:
            raise ValueError(f"Missing S3 bucket or key")
 
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