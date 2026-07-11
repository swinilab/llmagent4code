# ── Production-grade Dockerfile for OMS backend ────────────────────────
# Multi-stage build for minimal final image size.

FROM python:3.12-slim AS builder

WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir uv && uv export --no-hashes --format requirements-txt > requirements.txt

FROM python:3.12-slim AS runner

WORKDIR /app

# Install system deps for asyncpg and uvloop
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Resource limits (reflecting target hardware: 4 cores, 98 GB RAM)
# The container is configured to use up to 4 CPUs and 4 GB RAM.
# See NFR 1.2 justification in the ADR.
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--loop", "uvloop", "--http", "httptools"]
