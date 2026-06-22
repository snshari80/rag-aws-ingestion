🧠 RAG AWS Ingestion Pipeline

A serverless Retrieval-Augmented Generation (RAG) ingestion pipeline built on AWS.

This project ingests documents (PDFs, images, etc.), transforms them into structured text, generates embeddings, and stores them in a vector database (OpenSearch) for downstream LLM applications.

----------------------------------------------------------------------------------------------------------------------------------------------

🚀 Features
📂 Document ingestion from S3
🔄 Automated ETL pipeline (Extract → Transform → Embed)
🧠 Embedding generation using Amazon Bedrock
🔍 Vector storage using OpenSearch
⚡ Serverless orchestration using Step Functions + Lambda
🔐 Secure access with Cognito / IAM
📡 Real-time ingestion status via AppSync (optional)

----------------------------------------------------------------------------------------------------------------------------------------------

🏗️ Architecture Overview
        Upload File
             ↓
        S3 (Input Bucket)
             ↓
     Step Functions Workflow
             ↓
   ┌───────────────┬────────────────┬────────────────┐
   ↓               ↓                ↓
Validation     Transformation     Embedding
(Lambda)        (Lambda)          (Lambda)
   ↓               ↓                ↓
   └──────────→ Processed S3 ←─────┘
                        ↓
                 Chunk + Embed
                        ↓
                OpenSearch (Vector DB)

----------------------------------------------------------------------------------------------------------------------------------------------

⚙️ How It Works
1. 📥 Ingestion
Files uploaded to S3 trigger the pipeline
Supported formats:
PDFs
Images (JPG, PNG, SVG)

2. ✅ Validation
Lambda validates file type & existence
Rejects unsupported formats

3. 🔄 Transformation
Extracts text from documents
For images:
Uses Rekognition + LLM captioning
Stores processed text in S3

4. 🧩 Chunking & Embedding
Documents are split into chunks
Embeddings generated using Bedrock models

5. 📦 Storage
Embeddings stored in OpenSearch index
Metadata includes:
Timestamp
Model used

----------------------------------------------------------------------------------------------------------------------------------------------

📁 Project Structure
.
├── lambda/                  # Lambda functions (validation, transform, embedding)
├── modules/                 # Terraform modules
│   ├── document-ingestion
│   ├── networking-resources
│   ├── persistence-resources
│   ├── question-answering
│   └── summarization
├── resources/              # GenAI related resources
├── examples/               # Sample usage
├── tests/                  # Test cases
├── main.tf                 # Entry Terraform config
├── variables.tf            # Input variables
├── outputs.tf              # Outputs
└── providers.tf            # AWS providers
🛠️ Tech Stack
AWS Services
S3
Lambda
Step Functions
OpenSearch
Bedrock
AppSync
Cognito
EventBridge
Frameworks
Terraform
LangChain (for parsing/processing)
📦 Prerequisites
AWS Account
Terraform ≥ 1.0
AWS CLI configured
Bedrock model access enabled
OpenSearch cluster (or provisioned via Terraform)

----------------------------------------------------------------------------------------------------------------------------------------------

🚀 Setup & Deployment
1. Clone repo
git clone https://github.com/snshari80/rag-aws-ingestion.git
cd rag-aws-ingestion
2. Initialize Terraform
terraform init
3. Configure variables
Create terraform.tfvars:
solution_prefix = "rag"
region          = "us-east-1"
4. Deploy
terraform apply
🔌 Usage
Upload a file
aws s3 cp sample.pdf s3://<input-bucket>/
Trigger ingestion
Automatically via pipeline
Or via AppSync mutation (if enabled)
📊 Outputs

After deployment:

S3 input bucket
Processed S3 bucket
GraphQL endpoint
Cognito credentials
OpenSearch index
💰 Cost Considerations
Major cost drivers:
OpenSearch cluster
Lambda execution
Bedrock embeddings

----------------------------------------------------------------------------------------------------------------------------------------------

👉 AWS RAG pipelines can cost significantly at scale depending on usage

🔐 Security
IAM-based access control
Cognito authentication for APIs
VPC isolation (optional)
Secrets managed via AWS Secrets Manager
⚠️ Known Issues / Gotchas
❌ Duplicate files are skipped
❌ Unsupported formats will fail validation
⚠️ OpenSearch connectivity issues → check VPC/IAM
⚠️ Bedrock models must be explicitly enabled
🧪 Troubleshooting
Issue	Cause	Fix
Cannot connect to OpenSearch	Network/IAM issue	Check VPC + permissions
File not processed	Already exists	Delete from processed bucket
Unsupported file	Wrong format	Upload valid type
🧹 Cleanup
terraform destroy

----------------------------------------------------------------------------------------------------------------------------------------------

Then manually:

Delete S3 buckets
Clear OpenSearch index
Remove CloudWatch logs
🔮 Future Improvements
Streaming ingestion
Hybrid search (keyword + vector)
Better chunking strategies
Multi-tenant support
LangGraph orchestration

----------------------------------------------------------------------------------------------------------------------------------------------

🤝 Contributing

Hari Nagarajan S

----------------------------------------------------------------------------------------------------------------------------------------------

📜 License

MIT

----------------------------------------------------------------------------------------------------------------------------------------------

🧠 Summary

This repo gives you a production-grade RAG ingestion backbone on AWS:

Fully serverless
Scalable ingestion pipeline
Ready for LLM apps
