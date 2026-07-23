# Dockerfile for the OMS API service.
# Multi-stage build:
#   1. Base: Python 3.12 slim with uv
#   2. Runtime: minimal image with installed packages
FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Runtime stage
FROM python:3.12-slim

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy application code
COPY oms/ /app/oms/
COPY .env /app/.env

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
  CMD python -c "import httpx; httpx.get('http://localhost:8000/health/live').raise_for_status()"

# Run with uvicorn
CMD ["uvicorn", "oms.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "8", "--loop", "uvloop", "--http", "httptools"]
