FROM python:3.12-slim

WORKDIR /app

# Ensure the persistence directory exists even when the named volume
# is not yet mounted (e.g. `docker run` without compose). The SQLite
# database file is written here so it survives container recreation (NFR 2.3).
RUN mkdir -p /app/data

# Install uv for fast dependency management
RUN pip install --no-cache-dir uv

# Copy dependency manifests and install (frozen, no dev deps)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy application source
COPY oms/ oms/

# Expose the FastAPI port
EXPOSE 8000

# Run with uvicorn (single worker for SQLite; scale horizontally with
# a shared DB like PostgreSQL for multi-worker write concurrency)
CMD ["uv", "run", "uvicorn", "oms.main:app", "--host", "0.0.0.0", "--port", "8000"]