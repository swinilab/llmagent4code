FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (only what's needed for asyncpg and uvloop)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY oms/ oms/

# Install Python dependencies from pyproject.toml
RUN pip install --no-cache-dir .

# Create non-root user
RUN useradd -m -u 1000 oms && chown -R oms:oms /app
USER oms

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')" || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "oms.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--loop", "uvloop", "--http", "httptools"]
