# Use official Python slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy dependency files first for caching
COPY pyproject.toml uv.lock* ./

# Install uv (a fast package manager) and project dependencies
RUN pip install --no-cache-dir uv && \
    uv sync --frozen

# Copy application source code
COPY . .

# Expose port 8000 for FastAPI
EXPOSE 8000

# Command to run the app
CMD ["uv", "run", "main.py"]
