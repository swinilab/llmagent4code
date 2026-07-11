# ──────────────────────────────────────────────────────────────────────
# Dockerfile – Order Management System
# Multi-stage build for minimal final image.
# ──────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies into a virtual environment
RUN uv venv /opt/venv && \
    . /opt/venv/bin/activate && \
    uv sync --no-dev

# ── Runtime stage ───────────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY oms/ ./oms/
COPY openapi.yaml ./

# Create data directory for SQLite
RUN mkdir -p /app/data

# Health check
HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health/ping')" || exit 1

EXPOSE 8000

CMD ["uvicorn", "oms.main:app", "--host", "0.0.0.0", "--port", "8000"]
