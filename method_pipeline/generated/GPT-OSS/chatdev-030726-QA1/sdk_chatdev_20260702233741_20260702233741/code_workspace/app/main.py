import uvicorn
from fastapi import FastAPI
from app.routers import customers, products, orders, payments, invoices

app = FastAPI(
    title="Order Management System API",
    version="1.0.0",
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs",
)

# Include routers with version prefix already in each router
app.include_router(customers.router)
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(payments.router)
app.include_router(invoices.router)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
