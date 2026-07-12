"""
Dockerfile — production-ready OMS Backend container.
Based on python:3.12-slim for minimal image size.
"""
FROM python:3.12-slim

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package manager)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Install dependencies via uv (fast, cached)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy application code
COPY . .

# Non-root user for security
RUN useradd --create-home --shell /bin/bash omsuser && chown -R omsuser:omsuser /app
USER omsuser

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run via gunicorn (production) or uvicorn (development)
CMD ["gunicorn", "-c", "infra/gunicorn.conf.py", "server:app"]
