# Infrastructure as Code (IaC)

## Docker Deployment

### Build and Run with Docker Compose

```bash
cd iac
docker-compose up --build -d
```

### Check Status

```bash
docker-compose ps
docker-compose logs -f oms
```

### Health Check

```bash
curl http://localhost:8000/api/v1/health/live
```

### Stop

```bash
docker-compose down
```

### Stop and Remove Volumes

```bash
docker-compose down -v
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| DATABASE_URL | sqlite+aiosqlite:///./data/oms.db | Database connection string |
| HOST | 0.0.0.0 | Server host |
| PORT | 8000 | Server port |
| MAX_QUEUE_SIZE | 1000 | Maximum queue size |
| WORKER_COUNT | 4 | Number of queue workers |

## Production Considerations

For production deployment, consider:

1. **Database:** Replace SQLite with PostgreSQL for better concurrency
2. **Load Balancer:** Add nginx or similar in front of multiple instances
3. **Monitoring:** Integrate with Prometheus/Grafana
4. **Logging:** Centralized logging with ELK stack
5. **SSL/TLS:** Add HTTPS termination
6. **Secrets Management:** Use environment variables or vault for sensitive data
