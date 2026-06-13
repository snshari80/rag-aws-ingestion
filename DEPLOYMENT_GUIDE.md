# RAG Ingestion Pipeline - GitHub Deployment Guide

**Date**: June 12, 2026  
**Repository**: https://github.com/snshari80/rag-ingestion-pipeline  
**Version**: 1.0.0

---

## Table of Contents

1. [GitHub Secrets Configuration](#1-github-secrets-configuration)
2. [Dockerfile Setup](#2-dockerfile-setup)
3. [GitHub Actions Workflow](#3-github-actions-workflow)
4. [AWS Secrets Manager Integration](#4-aws-secrets-manager-integration)
5. [ECS Task Definition](#5-ecs-task-definition)
6. [Deployment Checklist](#6-deployment-checklist)
7. [Troubleshooting](#7-troubleshooting)

---

## 1. GitHub Secrets Configuration

### Step-by-Step Guide

**Location**: Go to your repository on GitHub

```
Settings → Secrets and variables → Actions → New repository secret
```

### Required Secrets to Add

| Secret Name | Value | Example |
|-------------|-------|---------|
| `AWS_REGION` | Your AWS region | `us-east-1` |
| `AWS_ACCOUNT_ID` | Your AWS account ID | `123456789012` |
| `AWS_ACCESS_KEY_ID` | Your IAM access key | `AKIA...` |
| `AWS_SECRET_ACCESS_KEY` | Your IAM secret key | `wJal...` |
| `S3_BUCKET_NAME` | Your S3 bucket name | `rag-documents-bucket-hari73` |
| `SQS_QUEUE_URL` | Main SQS queue URL | `https://sqs.us-east-1.amazonaws.com/123456789012/rag-ingestion-queue` |
| `SQS_DLQ_URL` | Dead letter queue URL | `https://sqs.us-east-1.amazonaws.com/123456789012/rag-ingestion-dlq` |
| `OPENSEARCH_HOST` | OpenSearch domain endpoint | `https://search-rag-vector-indexdoc-a2vel4wmwlxbac4cqfwgksisv4.us-east-1.es.amazonaws.com` |
| `OPENSEARCH_USERNAME` | OpenSearch username | `admin` |
| `OPENSEARCH_PASSWORD` | OpenSearch password | `Srivijay1997@` |
| `BEDROCK_REGION` | Bedrock region | `us-east-1` |

**Security Note**: Never expose these values in code or logs.

---

## 2. Dockerfile Setup

Create a file named `Dockerfile` in your repository root:

```dockerfile
# Use official Python runtime as base image
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies (if needed)
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY config.py .
COPY document_parse.py .
COPY embeddings.py .
COPY ingestion_pipeline.py .
COPY opensearch.py .
COPY sqs_worker.py .

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import boto3; boto3.client('sqs')" || exit 1

# Run the worker
CMD ["python", "sqs_worker.py"]
```

**File location**: `/Dockerfile` (repository root)

---

## 3. GitHub Actions Workflow

Create directory and file: `.github/workflows/deploy.yml`

```yaml
name: Deploy RAG Pipeline to ECS

on:
  push:
    branches: [ main ]
  workflow_dispatch:

env:
  AWS_REGION: ${{ secrets.AWS_REGION }}
  AWS_ACCOUNT_ID: ${{ secrets.AWS_ACCOUNT_ID }}
  ECR_REGISTRY: ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.${{ secrets.AWS_REGION }}.amazonaws.com
  ECR_REPOSITORY: rag-ingestion-pipeline
  IMAGE_TAG: ${{ github.sha }}

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write

    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v1

      - name: Build Docker image
        uses: docker/build-push-action@v4
        with:
          context: .
          push: true
          tags: |
            ${{ env.ECR_REGISTRY }}/${{ env.ECR_REPOSITORY }}:${{ env.IMAGE_TAG }}
            ${{ env.ECR_REGISTRY }}/${{ env.ECR_REPOSITORY }}:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Update ECS Task Definition
        id: task-def
        uses: aws-actions/amazon-ecs-render-task-definition@v1
        with:
          task-definition: ecs-task-definition.json
          container-name: rag-worker
          image: ${{ env.ECR_REGISTRY }}/${{ env.ECR_REPOSITORY }}:${{ env.IMAGE_TAG }}

      - name: Deploy to Amazon ECS
        uses: aws-actions/amazon-ecs-deploy-task-definition@v1
        with:
          task-definition: ${{ steps.task-def.outputs.task-definition }}
          service: rag-ingestion-service
          cluster: rag-cluster
          wait-for-service-stability: true

      - name: Notify Deployment Success
        if: success()
        run: echo "✅ Deployment successful! Image: ${{ env.ECR_REGISTRY }}/${{ env.ECR_REPOSITORY }}:${{ env.IMAGE_TAG }}"

      - name: Notify Deployment Failure
        if: failure()
        run: echo "❌ Deployment failed. Check logs above."
```

**File location**: `.github/workflows/deploy.yml`

---

## 4. AWS Secrets Manager Integration

For storing sensitive data securely (preferred over GitHub secrets):

### Create Secret in AWS

```bash
aws secretsmanager create-secret \
    --name rag-pipeline/opensearch-password \
    --secret-string "Srivijay1997@" \
    --region us-east-1
```

### Reference in ECS Task Definition

```json
{
  "name": "OPENSEARCH_PASSWORD",
  "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789012:secret:rag-pipeline/opensearch-password:password::"
}
```

**Benefits**:
- ✅ Centralized secret management
- ✅ Automatic rotation support
- ✅ Audit trail
- ✅ Fine-grained access control

---

## 5. ECS Task Definition

Create file: `ecs-task-definition.json`

```json
{
  "family": "rag-ingestion-worker",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "containerDefinitions": [
    {
      "name": "rag-worker",
      "image": "ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com/rag-ingestion-pipeline:latest",
      "essential": true,
      "portMappings": [],
      "environment": [
        {
          "name": "AWS_REGION",
          "value": "us-east-1"
        },
        {
          "name": "S3_BUCKET_NAME",
          "value": "rag-documents-bucket-hari73"
        },
        {
          "name": "S3_PREFIX_FILTER",
          "value": "documents/"
        },
        {
          "name": "SQS_BATCH_SIZE",
          "value": "1"
        },
        {
          "name": "SQS_WAIT_SECONDS",
          "value": "20"
        },
        {
          "name": "WORKER_CONCURRENCY",
          "value": "1"
        },
        {
          "name": "OPENSEARCH_INDEX_NAME",
          "value": "rag-vector-indexdoc"
        },
        {
          "name": "BEDROCK_REGION",
          "value": "us-east-1"
        }
      ],
      "secrets": [
        {
          "name": "SQS_QUEUE_URL",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789012:secret:rag-pipeline/sqs-queue-url"
        },
        {
          "name": "SQS_DLQ_URL",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789012:secret:rag-pipeline/sqs-dlq-url"
        },
        {
          "name": "OPENSEARCH_HOST",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789012:secret:rag-pipeline/opensearch-host"
        },
        {
          "name": "OPENSEARCH_USERNAME",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789012:secret:rag-pipeline/opensearch-username"
        },
        {
          "name": "OPENSEARCH_PASSWORD",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789012:secret:rag-pipeline/opensearch-password"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/rag-ingestion-worker",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ],
  "executionRoleArn": "arn:aws:iam::123456789012:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::123456789012:role/ecsTaskRole"
}
```

Replace:
- `ACCOUNT_ID` with your AWS account ID
- `REGION` with your AWS region
- ARN values with your actual AWS Secrets Manager ARNs

---

## 6. Deployment Checklist

### Pre-Deployment

- [ ] GitHub repository created and code pushed
- [ ] GitHub Secrets configured (11 secrets added)
- [ ] Dockerfile created and tested locally
- [ ] AWS account with appropriate permissions
- [ ] ECR repository created: `rag-ingestion-pipeline`
- [ ] ECS cluster created: `rag-cluster`
- [ ] ECS service created: `rag-ingestion-service`
- [ ] IAM roles configured (ecsTaskExecutionRole, ecsTaskRole)
- [ ] CloudWatch logs group created: `/ecs/rag-ingestion-worker`

### Deployment Steps

1. **Create AWS Resources** (one-time setup)
   ```bash
   # Create ECR repository
   aws ecr create-repository --repository-name rag-ingestion-pipeline --region us-east-1
   
   # Create CloudWatch logs group
   aws logs create-log-group --log-group-name /ecs/rag-ingestion-worker --region us-east-1
   ```

2. **Push Dockerfile and Workflows**
   ```bash
   git add Dockerfile .github/workflows/deploy.yml ecs-task-definition.json
   git commit -m "Add Docker and deployment configurations"
   git push origin main
   ```

3. **GitHub Actions Automatically**
   - Builds Docker image
   - Pushes to ECR
   - Updates ECS task definition
   - Deploys to ECS Fargate

4. **Monitor Deployment**
   - Go to GitHub Actions tab
   - Watch the build progress
   - Check ECS console for running tasks

### Post-Deployment

- [ ] Verify ECS task is running
- [ ] Check CloudWatch logs for errors
- [ ] Send test SQS message to queue
- [ ] Verify documents are being processed
- [ ] Monitor OpenSearch for indexed documents

---

## 7. Troubleshooting

### Issue: ECR Login Failed

**Solution**:
```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com
```

### Issue: ECS Task Fails to Start

**Check CloudWatch Logs**:
```bash
aws logs tail /ecs/rag-ingestion-worker --follow
```

**Common Causes**:
- Docker image not found in ECR
- Incorrect environment variables
- IAM role permissions insufficient
- Memory/CPU allocation too low

### Issue: SQS Messages Not Processing

**Verify**:
1. Task is running: `aws ecs list-tasks --cluster rag-cluster`
2. Queue has messages: `aws sqs get-queue-attributes --queue-url <URL> --attribute-names ApproximateNumberOfMessages`
3. Queue URL is correct in task definition

### Issue: OpenSearch Connection Timeout

**Verify**:
1. OpenSearch domain is publicly accessible
2. Security group allows inbound port 443
3. Credentials are correct
4. Endpoint URL has https://

### Enable Debug Logging

Add to `config.py`:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Rebuild and redeploy.

---

## Quick Reference Commands

```bash
# View running ECS tasks
aws ecs list-tasks --cluster rag-cluster

# Get task details
aws ecs describe-tasks --cluster rag-cluster --tasks <task-arn>

# View logs
aws logs tail /ecs/rag-ingestion-worker --follow

# Stop a task
aws ecs stop-task --cluster rag-cluster --task <task-arn>

# View GitHub Actions logs
# Go to: GitHub → Actions → [workflow run] → Deploy RAG Pipeline to ECS

# Check ECR image
aws ecr describe-images --repository-name rag-ingestion-pipeline

# Manual deployment without code push
aws ecs update-service --cluster rag-cluster --service rag-ingestion-service --force-new-deployment
```

---

## Support & Documentation

- **AWS ECS**: https://docs.aws.amazon.com/ecs/
- **GitHub Actions**: https://docs.github.com/en/actions
- **AWS Secrets Manager**: https://docs.aws.amazon.com/secretsmanager/
- **Repository**: https://github.com/snshari80/rag-ingestion-pipeline

---

**Document Version**: 1.0.0  
**Last Updated**: June 12, 2026
