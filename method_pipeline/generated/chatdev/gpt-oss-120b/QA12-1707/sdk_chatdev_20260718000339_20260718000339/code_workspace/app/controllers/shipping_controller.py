from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from ..services.order_service import OrderService
from ..database import get_session

router = APIRouter(prefix="/shipping", tags=["shipping"])

@router.post("/{order_id}/", status_code=status.HTTP_202_ACCEPTED)
def ship_order(order_id: int, session: Session = Depends(get_session)):
    try:
        OrderService.ship_order(session, order_id)
        return {"detail": "Shipping scheduled"}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
