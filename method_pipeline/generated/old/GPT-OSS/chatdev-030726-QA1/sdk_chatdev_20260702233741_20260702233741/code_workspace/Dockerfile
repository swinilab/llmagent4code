# Use official Python image
FROM python:3.11-slim

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run migrations / init db (optional)
# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
# Use reload in dev
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
