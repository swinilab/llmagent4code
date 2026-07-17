
\"\"\"
Main entry point for the OMS Backend.
\"\"\"
import uvicorn
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from oms_backend.database.db import init_db, ProductDB, engine
from oms_backend.controllers.order_controller import router
from sqlalchemy import insert, select
from sqlalchemy.exc import SQLAlchemyError

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Production Order Management System", version="1.0.0")

# --- NFR 2.1 & 2.2: Global Exception Middleware for Fault Recovery ---
@app.middleware("http")
async def resilience_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except SQLAlchemyError as exc:
        logger.error(f"Database error occurred: {str(exc)}")
        # Return a "Degraded Mode" response instead of a generic 500
        return JSONResponse(
            status_code=503,
            content={
                "error": "Service Temporarily Degraded",
                "message": "We are experiencing high load or database issues. Please try again in a moment.",
                "code": "SERVICE_DEGRADED"
            }
        )
    except Exception as exc:
        logger.exception(f"Unexpected system error: {str(exc)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "message": "An unexpected error occurred. Our engineers are notified.",
                "code": "INTERNAL_ERROR"
            }
        )

app.include_router(router)

@app.on_event(\"startup\")
async def startup_event():
    # Initialize Database
    await init_db()
    
    # Seed initial products for testing
    async with engine.connect() as conn:
        # Check if products exist to avoid duplicates on restart
        res = await conn.execute(select(ProductDB))
        if not res.scalars().all():
            products = [
                {\"description\": \"Laptop\", \"base_price\": 1200.0, \"currency\": \"USD\"},
                {\"description\": \"Mouse\", \"base_price\": 25.0, \"currency\": \"USD\"},
                {\"description\": \"Keyboard\", \"base_price\": 75.0, \"currency\": \"USD\"},
            ]
            await conn.execute(insert(ProductDB), products)
            await conn.commit()

@app.get(\"/health\")
async def health_check():
    return {\"status\": \"healthy\", \"timestamp\": \"now\"}

if __name__ == \"__main__\":\n    uvicorn.run(\"main:app\", host=\"0.0.0.0\", port=8000, reload=True)
