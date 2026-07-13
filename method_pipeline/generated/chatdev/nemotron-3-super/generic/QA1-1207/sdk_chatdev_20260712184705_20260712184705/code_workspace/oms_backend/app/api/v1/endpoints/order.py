from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from oms_backend.app.db.session import get_db
from oms_backend.app.schemas.order import OrderCreate, OrderCreateWithItems, OrderUpdate, Order
from oms_backend.app.services import order_service
from oms_backend.app.schemas.invoice import Invoice
from oms_backend.app.schemas.payment import Payment
from oms_backend.app.models.payment import PaymentMethod
router = APIRouter()

@router.get("/", response_model=list[Order])
def read_orders(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    orders = order_service.get_orders(db, skip=skip, limit=limit)
    return orders

@router.post("/", response_model=Order, status_code=status.HTTP_201_CREATED)
def create_order(order_in: OrderCreateWithItems, db: Session = Depends(get_db)):
    order = order_service.create_order_with_items(db, order_in, order_in.items)
    if not order:
        raise HTTPException(status_code=400, detail="Invalid product in items")
    return order

@router.get("/{order_id}", response_model=Order)
def read_order(order_id: int, db: Session = Depends(get_db)):
    db_obj = order_service.get_order(db, order_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Order not found")
    return db_obj

@router.put("/{order_id}", response_model=Order)
def update_order(order_id: int, order_in: OrderUpdate, db: Session = Depends(get_db)):
    db_obj = order_service.get_order(db, order_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Order not found")
    updated = order_service.update_order(db, order_id, order_in)
    return updated

@router.delete("/{order_id}", response_model=Order)
def delete_order(order_id: int, db: Session = Depends(get_db)):
    db_obj = order_service.get_order(db, order_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Order not found")
    deleted = order_service.delete_order(db, db_obj.id)
    return deleted

# Order items endpoints
from oms_backend.app.schemas.order_item import OrderItemCreate

item_router = APIRouter(prefix="/{order_id}/items", tags=["order_items"])

@item_router.post("/", response_model=dict)
def add_order_item(order_id: int, item_in: dict, db: Session = Depends(get_db)):
    item = OrderItemCreate(**item_in)
    db_item = order_service.add_order_item(db, order_id, item)
    if not db_item:
        raise HTTPException(status_code=400, detail="Product not found")
    return {"id": db_item.id}

@item_router.delete("/{item_id}", response_model=dict)
def remove_order_item(order_id: int, item_id: int, db: Session = Depends(get_db)):
    db_item = order_service.remove_order_item(db, item_id)
    if not db_item:
        raise HTTPException(status_code=404, detail="Order item not found")
    return {"id": item_id}

# Include the item router
router.include_router(item_router)