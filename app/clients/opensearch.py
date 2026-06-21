import argparse
from app.core.logger import logger
from datetime import datetime, timezone
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from app.core.config import (
    OPENSEARCH_HOST,
    OPENSEARCH_INDEX_NAME,
    OPENSEARCH_USERNAME,
    OPENSEARCH_PASSWORD,
    USE_AWS_OPENSEARCH,
    EMBEDDING_DIMENSIONS,
    AWS_REGION,
)

class OpenSearchVectorClient:
    def __init__(self):
        self.index_name = OPENSEARCH_INDEX_NAME
        self.client = self._build_client()
        logger.info(
            f"OpenSearch Vector Configured — host={OPENSEARCH_HOST}, "
            f"index={self.index_name}, aws_auth={USE_AWS_OPENSEARCH}"
            )

    def _build_client(self) -> OpenSearch:
        if USE_AWS_OPENSEARCH:
            credentials = boto3.Session().get_credentials()
            auth = AWSV4SignerAuth(credentials,AWS_REGION,"es")
        else:
            auth=(OPENSEARCH_USERNAME, OPENSEARCH_PASSWORD)
        
        return OpenSearch(
            hosts=[{"host": OPENSEARCH_HOST.replace("https://", "").replace("http://", ""), "port": 443}],
            http_auth=auth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            timeout=60,
        )

    def check_indexs_exist(self)->None:
        if self.client.indices.exists(index=self.index_name):
            return logger.info(f"Index Exist:{self.index_name}") 

        index_body = {
            "settings": {
                "index": {
                    "knn": True,               # Enable kNN plugin
                    "knn.algo_param.ef_search": 100,
                    "number_of_shards": 1,
                    "number_of_replicas": 1,
                }
            },
            "mappings": {
                "properties": {
                    # ── Vector field ──
                    "embedding": {
                        "type": "knn_vector",
                        "dimension": EMBEDDING_DIMENSIONS,
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",  # Cosine similarity
                            "engine": "faiss",
                            "parameters": {
                                "ef_construction": 128,
                                "m": 24,
                            },
                        },
                    },
                    # ── Content field (for BM25 / keyword fallback) ──
                    "content": {"type": "text", "analyzer": "english"},

                    # ── Metadata fields ──
                    "source_bucket":   {"type": "keyword"},
                    "source_key":      {"type": "keyword"},
                    "file_name":       {"type": "keyword"},
                    "file_type":       {"type": "keyword"},
                    "chunk_index":     {"type": "integer"},
                    "total_chunks":    {"type": "integer"},
                    "document_hash":   {"type": "keyword"},  # SHA-256 of original file
                    "ingested_at":     {"type": "date"},
                    "last_modified":   {"type": "keyword"},
                }
            },
        }

        self.client.indices.create(index=self.index_name, body=index_body)
        logger.info(f"Created index '{self.index_name}' with kNN vector mapping")

    def upsert_chunks(self,chunks:list,embeddings:list,meta_data:dict)->int:
        
        total_chunk = len(chunks)
        total_embeddings = len(embeddings)

        if total_chunk != total_embeddings:
            raise ValueError(f"Chunk count ({total_chunk}) != embedding count ({total_embeddings})")

        date_now = datetime.now(timezone.utc).isoformat()

        bulk_body = []

        for idx, (chunk_text, vector) in enumerate(zip(chunks,embeddings)):
            doc_id = f"{meta_data['source_key']}::chunk_{idx}"

            doc = {
                "embedding" : vector,
                "content" : chunk_text,
                "source_bucket": meta_data.get("source_bucket", ""),
                "source_key":    meta_data.get("source_key", ""),
                "file_name":     meta_data.get("file_name", ""),
                "file_type":     meta_data.get("file_type", ""),
                "chunk_index":   idx,
                "total_chunks":  total_chunk,
                "document_hash": meta_data.get("document_hash", ""),
                "ingested_at":   date_now,
                "last_modified": meta_data.get("last_modified", ""),
                }

            bulk_body.append({"index":{"_index":self.index_name, "_id":doc_id}})
            bulk_body.append(doc)
    

        try:
            response = self.client.bulk(body=bulk_body,refresh=True)
            errors = [item for item in response["items"] if "error" in item.get("index", {})]
            if errors:
                logger.error(f"Bulk insert had {len(errors)} errors: {errors[:2]}")

            inserted = total_chunk - len(errors)
            logger.info(f"Upserted {inserted}/{total_chunk} chunks into OpenSearch")
            return inserted
        except Exception as e:
            raise e

    def document_exist(self,source:str):
        query = {
            "size":1,
            "query":{ "term" : {"source_key":source}},
            "_source":["document_hash"]
        }
        try:
            repsonse = self.client.search(index=self.index_name,body=query)
            is_available = repsonse["hits"]["hits"]
            if is_available:
                return {
                    "exists":True,
                    "document_hash":is_available[0]["_source"]["document_hash"]
                }
            else:
                return { "exist":False}
        except Exception as e:
            logger.error(f"Error While Fetching the Document Search:{e} Source:{source}")
            return { "exist":False}
        
    def delete_document(self,source:str)->int:
        query = {"query":{"term":{"source_key":source}}}
        response = self.client.delete_by_query(
            index=self.index_name,
            body=query,
            refresh=True
        )
        if len(response["failures"]) == 0:
            deleted = response.get("deleted",0)
            logger.info(f"Document Deleted :{deleted}")
            return deleted
        
    def search(self, 
        query_vector:list,
        top_k:int =5,
        filter_file_type:str |None = None
        )->list:
        knn_query = {
            "vector": query_vector,
            "k":top_k
        }
        query_body = {
            "size":top_k,
            "query":{"knn" : {"embedding" : knn_query}},
            "_source":{"exclude" : ["embedding"]}
        }
        response = self.client.search(index=self.index_name,body=query_body)

        hits = response["hits"]["hits"]

        results = []
        for hit in hits:
            src = hit["_source"]
            results.append({
                "content": src.get("content",""),
                "score":hit["_score"],
                "file_name": src.get("file_name",""),
                "source_key": src.get("source_key", ""),
                "file_type" : src.get("file_type",""),
                "chunk_index": src.get("chunk_index",0),
                "total_chunks":src.get("total_chunks",""),
                "document_hash":src.get("document_hash",""),
                "ingested_at":src.get("ingested_at",""),
            })
        return results
    
    def _list_documents(self):
        query = {
            "size" : 0,
            "aggs":{
                "unique_dcos":{
                    "terms":{
                        "field":"source_key",
                        "size":100,
                    }
                }
            }
        }
        try:
            response = self.client.search(index=self.index_name, body=query)
            buckets = response["aggregations"]["unique_dcos"]["buckets"]

            if not buckets:
                print(f"No Buckets in index -> {self.index_name}")
            
            print(f"\n{'*'*60}")
            print(f"Unique Documents")
            print(f"Total available Documents: {len(buckets)}")
            for b in buckets:
                print(f"\n{b["key"]}")
            print(f"\n{'-'*60}")
           

        except Exception as e:
            logger.error(f"Error fetching list document -> {e}")
            print('error')
    
    def run(self):
        print("Running worker")

if __name__=="__main__":
    parser = argparse.ArgumentParser(description="OpenSearch List Documents")
    parser.add_argument(
        "--list_docs",
        action="store_true",
        help="List all documents currently stored in the index",
    )
    args = parser.parse_args()
    worker = OpenSearchVectorClient()
    if args.list_docs:
        worker._list_documents()
    else:

        worker.run()

