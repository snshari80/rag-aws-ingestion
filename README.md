# RAG AWS Ingestion Pipeline

A Python-based document ingestion worker for building retrieval-augmented generation (RAG) applications on AWS. The service listens for S3 upload events through SQS, downloads the document, extracts text, splits it into chunks, generates embeddings with Amazon Bedrock, and stores the results in OpenSearch for semantic search.

## What this project does

This repository implements the ingestion side of a RAG pipeline:

1. An S3 object upload triggers a message in SQS.
2. A worker process receives the message.
3. The document is downloaded to a temporary file.
4. Text is extracted from PDF, DOCX, or HTML content.
5. The text is chunked and embedded.
6. Chunks and vectors are upserted into OpenSearch.

## Architecture

- SQS worker: polls messages from an SQS queue and processes each document.
- Ingestion pipeline: orchestrates download, parsing, embedding, and indexing.
- Document parser: extracts text from supported file formats.
- Bedrock embeddings: generates vector embeddings for each chunk.
- OpenSearch client: creates and manages the vector index, then stores/retrieves chunks.

## Project structure

- app/clients: AWS/OpenSearch clients
- app/core: configuration and logging
- app/embeddings: Bedrock embedding integration
- app/parsers: document loaders and text extraction
- app/pipeline: ingestion orchestration logic
- app/scripts: helper scripts such as SQS setup
- app/worker: SQS consumer implementation
- main.py: entry point for the worker
- docker-compose.yml: local SQS + worker development stack
- Dockerfile: container image for running the worker

## Requirements

- Python 3.11+
- AWS credentials configured for S3, SQS, Bedrock, and OpenSearch
- An OpenSearch domain or compatible endpoint
- Access to a Bedrock embedding model

## Setup

1. Clone the repository
   ```bash
   git clone <repo-url>
   cd rag-dev
   ```

2. Create and activate a virtual environment
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
   On Windows PowerShell:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

3. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

4. Create a environment file
   ```bash
   cp .env.example .env
   ```
   If you do not have an example file yet, add the required variables manually. At minimum, configure:
   ```env
   AWS_REGION=us-east-1
   S3_BUCKET_NAME=your-bucket
   SQS_QUEUE_URL=your-queue-url
   SQS_DLQ_URL=your-dlq-url
   OPENSEARCH_HOST=https://your-opensearch-endpoint
   OPENSEARCH_INDEX_NAME=rag-documents
   OPENSEARCH_USERNAME=your-username
   OPENSEARCH_PASSWORD=your-password
   BEDROCK_REGION=us-east-1
   BEDROCK_EMBEDDING_MODEL_ID=your-model-id
   BEDROCK_LLM_MODEL_ID=your-llm-model-id
   ```

## Queue setup

If you need to create the SQS queues first, run:

```bash
python -m app.scripts.sqs_setup
```

## Running the worker

Run the worker locally:

```bash
python main.py
```

## Local development with Docker Compose

This repository includes a local stack for testing SQS locally with LocalStack:

```bash
docker compose up --build
```

The compose setup creates LocalStack-backed SQS queues and starts the ingestion worker container.

## Supported document types

- PDF
- DOCX
- HTML

## Notes

- The worker expects S3 events in the form produced by object upload notifications.
- Unsupported file types are skipped.
- The OpenSearch index is created automatically when the worker starts if it does not already exist.

## Next steps

You can extend this project by adding:

- additional parsers for more file types
- a REST API or search endpoint
- deployment automation for ECS, Lambda, or containerized infrastructure
