# ── Build Stage ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml .
RUN uv lock && uv venv && uv sync --no-dev

# ── Runtime Stage ───────────────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy application code
COPY app/ /app/app/

# Expose ports
EXPOSE 8000 9090

# Run with uvicorn
# 8 workers × 4096 limit_concurrency = 32768 theoretical concurrent connections
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "8", "--limit-concurrency", "4096", "--log-level", "info"]
