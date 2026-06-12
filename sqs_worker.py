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

# simple_msg = {
#   'MessageId': '5451f93e-f8ce-4b9d-837a-4dcf970a56eb',
#   'ReceiptHandle': 'AQEB6HiUrrA2uLs2Kr2oS6EyROj//7W3pMuPFtZVqROvaXxAet18osBpJT7tO+yMX4Ryo5MQ542+anBd0lqdltHiZ1AetE2OQ9VyUQ+tr75mzPdMxN1Z9EvIP9g1idAmtYjOjPgcbazfYfsuMEHA80Qd6AGup/JUvtSxW8qWHfSio0s8iUT1VSGMq94k7ttKGH1mGQzhaHMP/ve9aIKILEb6JfAS8pk1+jf7Bt9wxaeWD2njriyr5CkdW8ViK8a2wrLbHSMy+oaazoHB3ALzUOPphaEOlgJuzIxp+WtVDHy2rAecqbKg2RMhtd/4v3lpWP2HK970TjROX06VTsdJmtS+96W2aZEBMqordwQQuU6PX2S2ucIdvPaKh6M/YCPnl3JghGEnF8z6j1L5rZ1KRsCSFA==',
#   'MD5OfBody': 'b2eaa4150f6c987fe69b07592a2b9dc7',
#   'Body': '{"Records":[{"eventVersion":"2.1","eventSource":"aws:s3","awsRegion":"us-east-1","eventTime":"2026-06-03T00:16:47.207Z","eventName":"ObjectCreated:Put","userIdentity":{"principalId":"AWS:AIDASTB6HHO7JYMZXFA3P"},"requestParameters":{"sourceIPAddress":"27.4.159.210"},"responseElements":{"x-amz-request-id":"EHM3TCABJWEYXWFK","x-amz-id-2":"nrMDuNi5qAg/MYfSeIxccN22ueEPdSgUy+tqYd2z2/tarznNrLIcl04Ry8ozI7kPNCO7Ampr2mwhIGCX0TtdlIFTH58Ispjn"},"s3":{"s3SchemaVersion":"1.0","configurationId":"MzFkNzkzYWUtMzdkOS00NjIyLWJhY2EtMjI4NGM3M2VlMDhl","bucket":{"name":"rag-documents-bucket-hari73","ownerIdentity":{"principalId":"A5L9TSSW23NST"},"arn":"arn:aws:s3:::rag-documents-bucket-hari73"},"object":{"key":"documents/science_chapter3.docx","size":1253353,"eTag":"79b04463c0b116a16d6193a79b24459a","sequencer":"006A1F726F211841CE"}}}]}',
#   'Attributes': {
#     'ApproximateReceiveCount': '1'
#   }
# }

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
            WaitTimeSeconds     = SQS_WAIT_SECONDS,   # Long-polling
            VisibilityTimeout   = SQS_VISIBILITY_TIMEOUT,
            AttributeNames      = ["ApproximateReceiveCount"],
        )
        return response.get("Messages", [])

    def _handle_message(self,message:dict):
        receipt_handle = message["ReceiptHandle"]
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