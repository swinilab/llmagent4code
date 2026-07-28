"""Payment router – allows customers to pay and accountants to verify payments.
"""

from fastapi import APIRouter, Depends, HTTPException

router = APIRouter()

@router.post("/payments/{payment_id}/verify", tags=["payment"])
async def verify_payment(payment_id: str, role: str = Depends()):
    if role != "ACCOUNTANT":
        raise HTTPException(status_code=403, detail="Only accountants can verify payments")
    # Verification logic omitted – would update payment status.
    return {"payment_id": payment_id, "status": "VERIFIED"}
