import boto3
from pathlib import Path
import logging
import tempfile
import os
import hashlib

from config import SUPPORTED_EXTENSIONS
from document_parse import DocumentParser
from embeddings import BedRockEmbeddings
from opensearch import OpenSearchVectorClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


class IngestionPipline:
    def __init__(self):
        self.s3 = boto3.client("s3")
        self.parser = DocumentParser()
        self.embeddings = BedRockEmbeddings()
        self.os_client = OpenSearchVectorClient()
        self.os_client.check_indexs_exist()


    def ingest(self,bucket:str,key:str):
        file_name = Path(key).name
        file_ext = Path(key).suffix.lower()
        tmp_path = None

        logger.info(f"Ingestion Started for file Name:{file_name}")
        try:
            if file_ext not in SUPPORTED_EXTENSIONS:
                message = f"unsupported file extension:{file_ext}"
                logger.info(message)
            
            logger.info(f"Step[1/4] Downloading file from S3 to temp")
            tmp_path, file_size, last_modified = self._stream_download(bucket,key)
            doc_hash = self._hash_file(tmp_path)

            doc_exist = self.os_client.document_exist(key)

            self.os_client.delete_document(key)

            if doc_exist["exist"]:
                stored_hash = doc_exist.get("document_hash","")
                if stored_hash == doc_hash:
                    msg = "No changes in Document -> skipping"
                    logger.info(f"{msg}")
                    return { "status" :"Skipping" , "reason" : msg}
                else:
                    msg = "Document updated -> Receiving New Hash"
                    deleted = self.os_client.delete_document(source=key)
                    logger.info(f"  Deleted {deleted} old chunks")
            else:
                logger.info("  Document is NEW — first-time ingestion")

            chunks = self.parser.parse(tmp_path, file_size, last_modified)

            if chunks and doc_hash:
                logger.info(f"Document Extracted & Chunk's avaliable -> Chunk Size:{len(chunks)} -> Path:{tmp_path} ")
                embeddings = self.embeddings.embedded_batch(chunks)
                logger.info(f"Embedding completed {len(embeddings)} vectors (dim=1536)")

                meta_data = {
                    "source_bucket" : bucket,
                    "source_key" : key,
                    "file_name" : file_name,
                    "file_type" : file_ext,
                    "document_hash":doc_hash,
                    "last_modified" : last_modified
                }

                logger.info(f"Step[4/4] Upserting documents data")
                inserted = self.os_client.upsert_chunks(chunks=chunks,embeddings=embeddings,meta_data=meta_data)
                
            
                result = {
                    "status":"Success",
                    "key":key,
                    "file_name":file_name,
                    "file_ext":file_ext,
                    "file_size":file_size,
                    "chunk_total":chunks,
                    "chunk_size":len(chunks),
                    "chunks_stored":inserted,
                    "doc_hash":doc_hash,
                    "last_modified" : last_modified
                }
                logger.info(f"[Pipeline] Complete — {result}")
                return result
            

        except Exception as e:
            raise e

        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
                logger.info(f"Cleared S3 Downloaded Temp File-> Path:{tmp_path}")

    def _hash_file(self, file_path:str):
        sha256 = hashlib.sha256()
        with open(file_path , 'rb') as f:
            for block in iter(lambda: f.read(8*1024*1024) ,b""):
                sha256.update(block)
        return sha256.hexdigest()



    def _stream_download(self,bucket:str, key:str):
        try:
            response = self.s3.get_object(Bucket=bucket, Key=key)
            last_modified = str(response.get("LastModified",""))
            suffix = Path(key).suffix

            tmp_fd, tmp_path = tempfile.mkstemp(suffix=suffix)

            file_size = 0
            chunk_size = 8* 1024 *1024

            with os.fdopen(tmp_fd, "wb") as f:
                for chunk in response["Body"].iter_chunks(chunk_size=chunk_size):
                    f.write(chunk)
                    file_size += len(chunk)

            return tmp_path, file_size, last_modified
        except Exception as e:
            logger.error(f"Couldn't be able to download and chunk this file :{key} reason:{e}")
            raise e
