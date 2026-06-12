import boto3
from config import (BEDROCK_REGION,BEDROCK_EMBEDDING_MODEL_ID,MAX_CHARS_PER_CALL, EMBEDDING_DIMENSIONS, MAX_RETRIES, RETRY_BACKOFF_SECONDS)
import logging
import json
import time

logger = logging.getLogger(__name__)

class BedRockEmbeddings:

    def __init__(self):
        self.client = boto3.client(
                service_name="bedrock-runtime",
                region_name=BEDROCK_REGION,
        )
        self.model_id = BEDROCK_EMBEDDING_MODEL_ID
        logger.info(f"BedrockEmbeddings initialized — model={self.model_id}, region={BEDROCK_REGION}")

    def _call_bedrock(self,text:str,attempt: int =1) -> list:
        payload = {
            "inputText":text,
        }
        try:
            response = self.client.invoke_model(
                modelId= self.model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(payload),
            )
            result = json.loads(response["body"].read())
            return result["embedding"]

        
        except Exception as e:
           raise e


    def _embed_text(self,text:str)->list:
        if not text or not text.strip():
            logger.error(f"Chunks are empty : {text}")
            return [0.0] * EMBEDDING_DIMENSIONS
        
        if len(text) > MAX_CHARS_PER_CALL:
            logger.warning(f"Text Limit exhausted {len(text)}")
        text = text[:MAX_CHARS_PER_CALL]
        
        return self._call_bedrock(text)

    def embedded_batch(self,chunks:list[str])->list:
        embedding = []
        chunks_length = len(chunks)

        for idx, text in enumerate(chunks):
            vector = self._embed_text(text)
            embedding.append(vector)
        
        if(idx+1) % 10 == 0 or (idx +1) == chunks_length:
            logger.info(f"Embedded  {idx+1}/{chunks_length} chunks")
        
        if idx < chunks_length - 1:
            time.sleep(0.1)
        
        logger.info(f"Batch embedding complete — {chunks_length} vectors generated")
        return embedding