# ─────────────────────────────────────────────────────────────────────────────
# Dockerfile — RAG Ingestion Worker (ECS Fargate)
#
# Build:   docker build -t rag-ingestion-worker .
# Run:     docker run --env-file .env rag-ingestion-worker
# ─────────────────────────────────────────────────────────────────────────────

# Slim Python 3.13 base — smaller image, faster ECR push
FROM python:3.13-slim

# Set working directory inside container
WORKDIR /app

# ── System dependencies ───────────────────────────────────────────────────────
# python-docx and pptx need libxml2. PyPDF2 needs nothing extra.
# lxml (used by BeautifulSoup) needs libxml2-dev at build time.
# Build tools needed for compiling any native dependencies.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libxml2-dev \
    libxslt-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ── Python dependencies ───────────────────────────────────────────────────────
# Copy requirements first so Docker layer cache is reused when only .py files change
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Application code ──────────────────────────────────────────────────────────
# Copy all Python source files
COPY config.py .
COPY document_parse.py .
COPY embeddings.py .
COPY opensearch.py .
COPY ingestion_pipeline.py .
COPY sqs_worker.py .
# COPY test_search.py .
# COPY test_bedrock_llm.py .
# COPY test_api.py .

# ── /tmp space ────────────────────────────────────────────────────────────────
# ECS Fargate ephemeral storage is configurable (20 GB default, up to 200 GB).
# The worker streams S3 files to /tmp before parsing.
# For very large files, increase ephemeralStorage in your ECS task definition.

# ── Security: run as non-root user ────────────────────────────────────────────
RUN useradd --create-home --shell /bin/bash appuser
USER appuser

# ── Entry point ───────────────────────────────────────────────────────────────
# ECS will run this command when the container starts.
CMD ["python", "sqs_worker.py"]
