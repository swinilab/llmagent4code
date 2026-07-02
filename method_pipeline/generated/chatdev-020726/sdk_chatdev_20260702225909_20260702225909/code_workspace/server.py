"""
Main entry point to launch the OMS application.

This module provides the server startup functionality using uvicorn.
"""
import uvicorn

from oms.app import app


def run(host: str = "0.0.0.0", port: int = 8000, reload: bool = False) -> None:
    """
    Run the OMS application server.
    
    Args:
        host: Host address to bind to (default: 0.0.0.0)
        port: Port number to listen on (default: 8000)
        reload: Enable auto-reload for development (default: False)
    """
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=reload,
        log_level="info",
        access_log=True,
    )


if __name__ == "__main__":
    run()
