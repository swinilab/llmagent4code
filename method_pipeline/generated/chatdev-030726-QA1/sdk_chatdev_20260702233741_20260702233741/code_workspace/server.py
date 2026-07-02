# server.py
"""Run the FastAPI application using uvicorn."""

import uvicorn

from app.main import app

def run(host: str = "0.0.0.0", port: int = 8000):
    """Start the ASGI server.

    Parameters
    ----------
    host: str
        Host address to bind.
    port: int
        Port number.
    """
    uvicorn.run(app, host=host, port=port, log_level="info")

if __name__ == "__main__":
    run()
