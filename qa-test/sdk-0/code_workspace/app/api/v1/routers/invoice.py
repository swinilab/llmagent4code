"""Invoice router – allows accountant to create invoice (already triggered via order router) and view invoice.
"""

from fastapi import APIRouter, Depends, HTTPException

router = APIRouter()

# For brevity, only a placeholder GET endpoint is provided.
@router.get("/invoices/{invoice_id}", tags=["invoice"])
async def get_invoice(invoice_id: str, role: str = Depends()):
    if role != "ACCOUNTANT":
        raise HTTPException(status_code=403, detail="Only accountants can view invoices")
    # Retrieval logic omitted – would query DB and return DTO.
    return {"invoice_id": invoice_id, "status": "ISSUED"}
