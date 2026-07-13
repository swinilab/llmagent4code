"""
Main entry point for the OMS backend.
"""
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from .controllers import router_user, router_product, router_order, router_payment, router_invoice
from .database import engine, SessionLocal
from . import models
from .middleware import LoadSheddingMiddleware

app = FastAPI(
    title="Order Management System (OMS)",
    description="Backend for customer ordering, payment processing, invoicing, shipping, and closure.",
    version="1.0.0",
)

# Add load shedding middleware
app.add_middleware(LoadSheddingMiddleware)

# Create tables on startup
@app.on_event("startup")
async def startup():
    models.Base.metadata.create_all(bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Include routers
app.include_router(router_user)
app.include_router(router_product)
app.include_router(router_order)
app.include_router(router_payment)
app.include_router(router_invoice)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Order Management System API"}

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint that verifies database connectivity."""
    try:
        # Execute a simple query to verify the database is reachable
        db.execute("SELECT 1")
        db_status = "ok"
    except OperationalError as e:
        db_status = f"error: {str(e)}"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database unhealthy: {db_status}",
        )
    return {
        "status": "healthy",
        "database": db_status,
    }