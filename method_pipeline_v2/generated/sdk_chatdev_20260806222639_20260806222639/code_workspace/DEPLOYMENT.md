# OMS Backend - Deployment Guide

## Prerequisites

- Docker and Docker Compose installed
- Or Python 3.12+ with uv package manager

## Quick Start with Docker (Recommended)

### 1. Start all services

```bash
cd iac
docker-compose up -d
```

This will start:
- PostgreSQL database on port 5432
- Redis cache on port 6379
- OMS Backend API on port 8000

### 2. Initialize the database

```bash
docker exec oms_postgres psql -U postgres -d oms_db -f /docker-entrypoint-initdb.d/init.sql
```

Or manually:

```bash
docker cp init_db.sql oms_postgres:/tmp/init.sql
docker exec oms_postgres psql -U postgres -d oms_db -f /tmp/init.sql
```

### 3. Verify the deployment

```bash
# Check health endpoint
curl http://localhost:8000/health

# Access API documentation
open http://localhost:8000/api/docs
```

### 4. Stop services

```bash
cd iac
docker-compose down
```

## Local Development (Without Docker)

### 1. Install dependencies

```bash
# Create virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install packages
uv sync
```

### 2. Start PostgreSQL

```bash
# Using Docker for PostgreSQL only
docker run -d --name oms_postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=oms_db \
  -p 5432:5432 \
  postgres:15-alpine
```

### 3. Start Redis

```bash
# Using Docker for Redis only
docker run -d --name oms_redis \
  -p 6379:6379 \
  redis:7-alpine
```

### 4. Initialize database

```bash
psql -U postgres -d oms_db -f iac/init_db.sql
```

### 5. Set environment variables

Create a `.env` file:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/oms_db
REDIS_URL=redis://localhost:6379/0
DEBUG=true
ENABLE_CACHING=true
ENABLE_RATE_LIMITING=true
```

### 6. Run the application

```bash
uv run python main.py
```

Or:

```bash
uvicorn oms_backend.server:app --reload --host 0.0.0.0 --port 8000
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| DATABASE_URL | postgresql://postgres:postgres@localhost:5432/oms_db | PostgreSQL connection string |
| REDIS_URL | redis://localhost:6379/0 | Redis connection string |
| DEBUG | false | Enable debug mode |
| ENABLE_CACHING | true | Enable Redis caching |
| ENABLE_RATE_LIMITING | true | Enable rate limiting |
| RATE_LIMIT_MAX_EVENTS | 100 | Max events per second |
| REDIS_CACHE_TTL | 300 | Cache TTL in seconds |

## Production Deployment

### Docker Compose (Production)

```bash
cd iac
docker-compose -f docker-compose.yml up -d --build
```

### Kubernetes (Optional)

For Kubernetes deployment, create:
- Deployment manifest for oms_backend
- StatefulSet for postgres
- StatefulSet for redis
- Services for each component
- ConfigMap for environment variables
- PersistentVolumeClaims for data

## Health Checks

- **API Health**: `GET /health`
- **Database**: PostgreSQL healthcheck in docker-compose
- **Redis**: Redis healthcheck in docker-compose

## Logs

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f oms_backend
docker-compose logs -f postgres
docker-compose logs -f redis
```

## Backup and Restore

### Database Backup

```bash
docker exec oms_postgres pg_dump -U postgres oms_db > backup.sql
```

### Database Restore

```bash
docker exec -i oms_postgres psql -U postgres -d oms_db < backup.sql
```

## Troubleshooting

### Database connection issues

```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Check logs
docker logs oms_postgres

# Test connection
docker exec oms_postgres psql -U postgres -d oms_db -c "SELECT 1"
```

### Redis connection issues

```bash
# Check if Redis is running
docker ps | grep redis

# Test connection
docker exec oms_redis redis-cli ping
```

### Application issues

```bash
# Check application logs
docker logs oms_backend

# Restart application
docker-compose restart oms_backend
```
