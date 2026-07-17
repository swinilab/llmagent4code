"""
Server module for running the OMS application.
Provides the run function to start the uvicorn server.
"""

import uvicorn
import logging

from oms.config.settings import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def run():
    """
    Run the OMS application server.
    Uses uvicorn ASGI server with configuration from settings.
    """
    logger.info(f"Starting OMS server on {config.HOST}:{config.PORT}")
    logger.info(f"Workers: {config.WORKERS}")
    
    uvicorn.run(
        "oms.app:app",
        host=config.HOST,
        port=config.PORT,
        workers=config.WORKERS,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    run()
