# syntax=docker/dockerfile:1

FROM node:22-bookworm-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend ./
ARG VITE_API_BASE=
ENV VITE_API_BASE=${VITE_API_BASE}
RUN npm run build

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend \
    CIRCUITSAGE_HOSTED=1 \
    CIRCUITSAGE_DEV=0 \
    FRONTEND_ORIGIN=https://circuitsage-api.fly.dev \
    CIRCUITSAGE_DATABASE_PATH=/data/circuitsage.db \
    CIRCUITSAGE_UPLOAD_DIR=/data/uploads \
    OLLAMA_BASE_URL=http://127.0.0.1:11434 \
    OLLAMA_MODEL=gemma4:e4b \
    OLLAMA_VISION_MODEL=gemma4:e4b \
    OLLAMA_MODELS=/data/ollama

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    curl \
    build-essential \
    pkg-config \
    libcairo2-dev \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    && rm -rf /var/lib/apt/lists/*
RUN curl -fsSL https://ollama.com/install.sh | sh || echo "Ollama install skipped; attach an Ollama sidecar or rely on deterministic fallback."

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend
COPY sample_data /app/sample_data
COPY docs /app/docs
COPY scripts /app/scripts
COPY README.md SPEC.md Makefile /app/
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

RUN chmod +x /app/scripts/hosted_start.sh

EXPOSE 8000
CMD ["/app/scripts/hosted_start.sh"]
