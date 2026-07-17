# Local Deployment Guide

## Prerequisites
- Python 3.10+
- uv (installed via `curl -LsSf https://astral.sh/uv/install.sh | sh`)

## Installation
1. Clone the repository.
2. Run `uv sync` to install all dependencies.

## Running the System
Execute the following command:
```bash
uv run python main.py
```
The server will start at `http://localhost:8000`.

## API Documentation
Access the interactive OpenAPI documentation at:
`http://localhost:8000/docs`

## Verification of NFRs
1. **Response Time (NFR 1.1):** Use `curl` or Postman to hit `/api/v1/products`. Observe sub-100ms response times.
2. **Concurrency (NFR 1.2):** Use `ab -n 1000 -c 10 http://localhost:8000/health` to verify handling of concurrent requests.
3. **State Preservation (NFR 2.3):** 
   - Place an order.
   - Stop the server (`Ctrl+C`).
   - Restart the server.
   - Query the order status; it should persist in `oms.db`.
4. **Graceful Degradation (NFR 2.1):** The system is designed as a monolith for this demo; however, the use of `async` ensures that slow DB queries don't block the entire event loop.
