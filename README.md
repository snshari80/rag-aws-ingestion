# RAG Ingestion Pipeline

A production-ready AWS-powered data ingestion engine for semantic document processing and vector embedding. Streams documents from S3, extracts text from multiple formats, generates embeddings via AWS Bedrock, and indexes them in OpenSearch for retrieval-augmented generation (RAG) applications.

## Features

- 📄 **Multi-format support**: PDF, DOCX, HTML, PPTX document parsing
- 🚀 **Streaming architecture**: Efficiently handles large files without memory spikes
- 🔍 **Semantic indexing**: AWS Bedrock Titan embeddings (1536-dimensional vectors)
- 🔄 **Change detection**: SHA-256 hashing prevents duplicate ingestion
- 📦 **Scalable**: Built for ECS Fargate with SQS job distribution
- 🏗️ **Production-ready**: Error handling, retry logic, cleanup for long-running tasks
- 🔐 **Secure**: Environment-based configuration, no hardcoded credentials

## Tech Stack

- **Runtime**: Python 3.13
- **Cloud**: AWS (S3, SQS, Bedrock, OpenSearch)
- **Core Libraries**: boto3, LangChain, langchain-community
- **Document Parsing**: docx2txt, PyPDF, python-pptx
- **Vector DB**: OpenSearch
- **Async**: aiohttp, asyncio

## Architecture

```
S3 Bucket
    ↓
SQS Queue (rag-ingestion-queue)
    ↓
ECS Fargate Task (sqs_worker.py)
    ├─ Stream download from S3 → /tmp
    ├─ SHA-256 hash (change detection)
    ├─ Check OpenSearch for existing docs
    ├─ Parse document (PDF/DOCX/HTML/PPTX)
    ├─ Bedrock embeddings (1536-dim)
    └─ Upsert into OpenSearch
    ↓
OpenSearch Vector Index
```

## Installation

### Prerequisites
- Python 3.13+
- AWS Account with:
  - S3 bucket
  - SQS queue (main + DLQ)
  - OpenSearch domain
  - Bedrock API access

### Setup

```bash
# Clone repository
git clone https://github.com/snshari80/rag-ingestion-pipeline.git
cd rag-ingestion-pipeline

# Create virtual environment
python -m venv venv

# Activate venv
# On Windows:
.\Scripts\Activate.ps1
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

1. **Copy environment template**
   ```bash
   cp .env.example .env
   ```

2. **Fill in your values in `.env`**
   ```env
   # AWS
   AWS_REGION=us-east-1
   S3_BUCKET_NAME=your-bucket-name
   
   # SQS
   SQS_QUEUE_URL=https://sqs.region.amazonaws.com/account-id/queue-name
   SQS_DLQ_URL=https://sqs.region.amazonaws.com/account-id/dlq-name
   
   # OpenSearch
   OPENSEARCH_HOST=https://your-domain.region.es.amazonaws.com
   OPENSEARCH_USERNAME=admin
   OPENSEARCH_PASSWORD=your-password
   
   # Bedrock
   BEDROCK_REGION=us-east-1
   ```

3. **Ensure AWS credentials are configured**
   ```bash
   # Option 1: AWS CLI
   aws configure
   
   # Option 2: Environment variables
   export AWS_ACCESS_KEY_ID=your-key
   export AWS_SECRET_ACCESS_KEY=your-secret
   ```

## Usage

### Running the Worker

```bash
python sqs_worker.py
```

The worker continuously polls the SQS queue and processes documents.

### Processing a Document Manually

```python
from ingestion_pipeline import IngestionPipeline

pipeline = IngestionPipeline()
result = pipeline.ingest(
    bucket="my-bucket",
    key="documents/annual_report.pdf"
)

print(result)
# {
#   "status": "success",
#   "chunks_total": 245,
#   "chunks_stored": 245,
#   "document_hash": "abc123...",
#   "file_size_mb": 15.32
# }
```

### SQS Message Format

Push this to SQS for processing:

```json
{
  "bucket": "rag-documents-bucket",
  "key": "documents/compliance_manual.pdf"
}
```

## Project Structure

```
rag-ingestion-pipeline/
├── config.py                 # Configuration & environment setup
├── document_parse.py         # Multi-format document parser
├── embeddings.py             # AWS Bedrock embeddings integration
├── opensearch.py             # OpenSearch client & vector operations
├── ingestion_pipeline.py     # Core orchestration logic
├── sqs_worker.py             # SQS polling & job processing
├── sqs_setup.py              # SQS queue initialization script
├── requirements.txt          # Python dependencies
├── .env.example              # Environment configuration template
├── .gitignore                # Git ignore rules
├── notification.json         # SNS notification templates
└── README.md                 # This file
```

## API Reference

### IngestionPipeline

```python
class IngestionPipeline:
    def ingest(bucket: str, key: str) -> dict
```

**Returns:**
```python
{
    "status": "success|failed|skipped",
    "key": str,
    "chunks_total": int,
    "chunks_stored": int,
    "document_hash": str,
    "file_size_mb": float
}
```

### Supported File Types

- `.pdf` - Portable Document Format
- `.docx` - Microsoft Word (2007+)
- `.html`, `.htm` - HTML documents
- `.pptx` - Microsoft PowerPoint (2007+)
- `.ppt` - Microsoft PowerPoint (97-2003)

## Logging

The pipeline produces detailed logs:

```
[Pipeline] Starting ingestion — bucket=my-bucket, key=documents/report.pdf
[Step 1] Streaming download from S3 → /tmp ...
[Step 2] SHA-256: abc123def456...
[Step 3] Checking OpenSearch for existing document...
[Step 4] Parsing document (type=.pdf) ...
[Step 5] Generating embeddings for 50 chunks ...
[Step 6] Upserting 50 chunks into OpenSearch ...
[Pipeline] Complete — {'status': 'success', ...}
```

## Error Handling

The pipeline handles:
- **Unsupported file types** → Skipped with warning
- **S3 access errors** → Logged and raised
- **OpenSearch connectivity** → Retries with backoff
- **Bedrock rate limiting** → Exponential backoff
- **Parsing failures** → Document skipped, error logged

## Performance Notes

- **Streaming**: Large files (>100 MB) are streamed to /tmp to avoid memory exhaustion
- **Batch embeddings**: Multiple chunks sent to Bedrock in batches for efficiency
- **Change detection**: SHA-256 hashing skips unchanged documents
- **Cleanup**: /tmp files removed after processing (important for long-running ECS tasks)

## Troubleshooting

### SQS Queue Not Receiving Messages
```bash
python sqs_setup.py  # Recreate queues
```

### OpenSearch Connection Failed
- Verify domain is public or accessible from ECS task
- Check security group allows inbound on port 443
- Confirm credentials in `.env`

### Out of Memory During File Processing
- Switch to larger ECS task (current: streaming enabled)
- Reduce `SQS_BATCH_SIZE` in `.env`

### Embedding Generation Timeout
- Increase `MAX_RETRIES` in config.py
- Check Bedrock quota in AWS Console

## Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/your-feature`
3. Commit changes: `git commit -m 'Add feature'`
4. Push to branch: `git push origin feature/your-feature`
5. Open Pull Request

## License

MIT License - see LICENSE file for details

## Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Check existing documentation
- Review AWS Bedrock & OpenSearch documentation

## Author

**Siva Hari**  
GitHub: [@snshari80](https://github.com/snshari80)

---

**Last Updated**: 2026-06-12  
**Version**: 1.0.0
