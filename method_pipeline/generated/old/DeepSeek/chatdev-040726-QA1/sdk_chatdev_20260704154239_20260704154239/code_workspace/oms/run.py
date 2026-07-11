"""
This is the main module to launch the program.
Uses uvicorn with configurable workers for local development.
"""
import uvicorn
from app.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        workers=settings.uvicorn_workers,
    )
