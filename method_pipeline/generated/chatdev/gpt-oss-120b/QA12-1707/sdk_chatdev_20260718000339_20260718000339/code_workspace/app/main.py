"""Application entry point configuring FastAPI and routers."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import create_db_and_tables
from .controllers import (
    customer_router,
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        log_level="info",
    )

app = FastAPI(
    title="OMS Backend",
    version="1.0.0",
    description="Production‑grade Order Management System backend API",
)

# CORS (allow all for simplicity)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(customer_router)
app.include_router(product_router)
app.include_router(order_router)
app.include_router(invoice_router)
app.include_router(payment_router)

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

# Health check endpoint for monitoring
@app.get("/health", tags=["monitoring"])
def health_check():
    return {"status": "ok"}
