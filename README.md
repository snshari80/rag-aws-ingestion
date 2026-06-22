🧠 RAG AWS Ingestion Pipeline

RAG AWS Ingestion Pipeline
A serverless Retrieval-Augmented Generation (RAG) ingestion pipeline built on AWS.
This project ingests documents (PDFs, images, etc.), transforms them into structured text, generates embeddings, and stores them in a vector database (OpenSearch) for downstream LLM applications.

Repository:
https://github.com/snshari80/rag-aws-ingestion

Overview:
This project implements a serverless Retrieval-Augmented Generation (RAG) ingestion pipeline on AWS. It ingests documents, processes them, generates embeddings, and stores them in a vector database for downstream LLM applications.

Features:
- Document ingestion from S3
- ETL pipeline (Extract, Transform, Embed)
- Embedding generation using Amazon Bedrock
- Vector storage using OpenSearch
- Serverless orchestration with Step Functions and Lambda
- Secure access via IAM/Cognito

Architecture Flow:
Upload File → S3 → Step Functions → Validation Lambda → Transformation Lambda → Embedding Lambda → OpenSearch

How It Works:
1. Files are uploaded to S3
2. Validation Lambda checks file type
3. Transformation extracts text
4. Chunking and embedding is performed
5. Data is stored in OpenSearch

Project Structure:
- modules/: Terraform modules
- resources/: AI resources
- examples/: Sample usage
- tests/: Test cases
- main.tf: Entry Terraform config

Tech Stack:
AWS (S3, Lambda, Step Functions, OpenSearch, Bedrock, AppSync, Cognito)
Terraform
LangChain

Prerequisites:
- AWS Account
- Terraform >= 1.0
- AWS CLI configured
- Bedrock access enabled

Setup:
1. git clone https://github.com/snshari80/rag-aws-ingestion.git
2. terraform init
3. terraform apply

Usage:
Upload a file to S3 bucket:
aws s3 cp sample.pdf s3://<input-bucket>/

Cleanup:
terraform destroy

Notes:
- Unsupported formats will fail
- OpenSearch requires proper IAM/VPC setup
- Bedrock models must be enabled

License:
MIT
