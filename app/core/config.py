import os
from dotenv import load_dotenv
from pathlib import Path

if Path(".env.docker").exists():
    load_dotenv(".env.docker")
elif Path(".env").exists():
    load_dotenv(".env")

# AWS Configuration
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

# SQS Configuration
MAIN_QUEUE_NAME = "rag-ingestion-queue"
DLQ_NAME = "rag-ingestion-dlq"
SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL")
SQS_DLQ_URL = os.getenv("SQS_DLQ_URL")
SQS_VISIBILITY_TIMEOUT = int(os.getenv("SQS_VISIBILITY_TIMEOUT", "600"))
SQS_MAX_RECEIVE_COUNT = int(os.getenv("SQS_MAX_RECEIVE_COUNT", "3"))
SQS_BATCH_SIZE = int(os.getenv("SQS_BATCH_SIZE", "1"))
SQS_WAIT_SECONDS = int(os.getenv("SQS_WAIT_SECONDS", "20"))

# OpenSearch Configuration
OPENSEARCH_HOST = os.getenv("OPENSEARCH_HOST")
OPENSEARCH_INDEX_NAME = os.getenv("OPENSEARCH_INDEX_NAME")
OPENSEARCH_USERNAME = os.getenv("OPENSEARCH_USERNAME")
OPENSEARCH_PASSWORD = os.getenv("OPENSEARCH_PASSWORD")
USE_AWS_OPENSEARCH = os.getenv("USE_AWS_OPENSEARCH", "False").lower() == "true"

# Bedrock Configuration
BEDROCK_REGION = os.getenv("BEDROCK_REGION")
BEDROCK_EMBEDDING_MODEL_ID = os.getenv("BEDROCK_EMBEDDING_MODEL_ID")
EMBEDDING_DIMENSIONS = 1024

# Worker Configuration
WORKER_CONCURRENCY = int(os.getenv("WORKER_CONCURRENCY", "1"))
MAX_CHARS_PER_CALL = 30_000
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2

# Supported File Types
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".html"}