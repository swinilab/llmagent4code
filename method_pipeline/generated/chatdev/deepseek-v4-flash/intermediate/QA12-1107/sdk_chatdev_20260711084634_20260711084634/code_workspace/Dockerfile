# Dockerfile for the OMS application.
# Multi-stage build:
#   1. Base: Python 3.12 slim with dependencies.
#   2. Final: runtime image with application code.
FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --no-dev --frozen

FROM python:3.12-slim

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY oms/ /app/oms/
COPY pyproject.toml /app/

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app:$PYTHONPATH"
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health/live', timeout=5)"

# Run the application
CMD ["uvicorn", "oms.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
