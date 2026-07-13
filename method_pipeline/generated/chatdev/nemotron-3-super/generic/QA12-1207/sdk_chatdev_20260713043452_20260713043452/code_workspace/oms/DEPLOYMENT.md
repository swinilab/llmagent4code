# Deployment Guide

## Prerequisites

- Docker and Docker Compose installed
- Git (to clone the repository)

## Local Development

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd oms
   ```

2. Build and start the containers:
   ```bash
   docker-compose up --build
   ```

3. The API will be available at http://localhost:8000
   - API documentation: http://localhost:8000/docs
   - Alternative docs: http://localhost:8000/redoc

## Environment Variables

The application uses environment variables for configuration. 
Create a `.env` file in the root directory (or modify `docker-compose.yml`).

Key variables:
- `PROJECT_NAME`: Name of the project
- `VERSION`: API version
- `DATABASE_URL`: Database connection string (default: sqlite+aiosqlite:///./oms.db)
- `DB_ECHO`: Set to "True" to enable SQLAlchemy echo
- `SECRET_KEY`: Secret key for JWT (if authentication is added)
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Token expiration time

## Production Deployment

For production, use a production-ready ASGI server like Uvicorn with Gunicorn.
The provided `Dockerfile` uses Uvicorn directly, which is suitable for small to medium production loads.

To build for production:
```bash
docker build -t oms:prod .
```

To run with Docker Compose (using production settings):
```bash
docker-compose -f docker-compose.prod.yml up -d
```

Note: In production, you should:
1. Use a managed PostgreSQL database
2. Set strong secrets
3. Enable HTTPS (via reverse proxy like Nginx or Traefik)
4. Set up logging and monitoring
5. Consider using a process manager like systemd or Kubernetes

## Database Migrations

We use Alembic for database migrations.
To generate a new migration:
```bash
alembic revision --autogenerate -m "description"
```

To apply migrations:
```bash
alembic upgrade head
```

The Docker container runs migrations on startup via the `prestart.sh` script.

## Testing

Run the test suite:
```bash
docker-compose run --rm app pytest
```

## Scaling

To scale horizontally:
1. Use a load balancer in front of multiple API instances
2. Ensure the database can handle the concurrent connections
3. Consider using Redis for caching and background task queues

## Monitoring

The application exposes basic health checks:
- `GET /health` returns 200 if the application is running
- `GET /metrics` (if Prometheus client is added) for metrics

Add Prometheus and Grafana for detailed monitoring.
