# Use official Python slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies (if any)
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

# Copy pyproject and lock files
COPY pyproject.toml uv.lock ./

# Install uv (fast Python package manager) and install deps
RUN pip install --no-cache-dir uv && \
    uv sync --frozen

# Copy application source code
COPY . .

# Expose port for FastAPI
EXPOSE 8000

# Command to run the app with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
