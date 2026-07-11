"""
Dockerfile for the OMS backend.
Resource limits: 4 CPU cores (of 8 available), 4 GB RAM (of 98 GB available).
See ADR for justification.
"""
FROM python:3.12-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy project files
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

EXPOSE 8000
EXPOSE 9090

# Run with 4 workers (matching 4 allocated cores)
CMD ["uv", "run", "uvicorn", "oms.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
