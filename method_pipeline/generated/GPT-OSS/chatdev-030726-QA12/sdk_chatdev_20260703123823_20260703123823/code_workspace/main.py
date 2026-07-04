"""Application entry point.
Creates FastAPI app, includes routers, and runs via uvicorn.
"""
import uvicorn
from fastapi import FastAPI
from routers import customer, product, order
from database import Base, get_engine

app = FastAPI(title="Order Management System API", version="1.0.0")

# Include routers
app.include_router(customer.router)
app.include_router(product.router)
app.include_router(order.router)

# Create DB tables on startup (production would use migrations)
@app.on_event("startup")
def on_startup():
    engine = get_engine()
    Base.metadata.create_all(bind=engine)

def run():
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    run()
