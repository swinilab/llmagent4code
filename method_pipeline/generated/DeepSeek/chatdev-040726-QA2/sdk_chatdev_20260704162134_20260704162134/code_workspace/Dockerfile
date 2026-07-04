# syntax=docker/dockerfile:1
FROM python:3.12-slim

WORKDIR /app

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application code
COPY oms/ oms/
COPY .env .env

# Expose the application port
EXPOSE 8000

# Run the application
CMD ["uv", "run", "python", "-m", "oms.main"]
