"""InvoiceService – creates invoices for accepted orders.

Heavy work is performed asynchronously via the queue manager (NFR 1.3).
"""

import datetime
from decimal import Decimal

from app.db.models import Invoice, Order, OrderStatus
from app.persistence.wal import WAL

wal = WAL()

class InvoiceService:
    async def create_invoice(self, order_id: str):
        async with Order.async_session() as session:
            order = await session.get(Order, order_id)
            if not order:
                raise ValueError("Order not found")
            if order.status != OrderStatus.ACCEPTED:
                raise ValueError("Invoice can only be created for ACCEPTED orders")
            # Snapshot billing info from customer (omitted for brevity – assume static)
            billing_info = {"name": "Customer Name", "address": "Customer Address"}
            issue_date = datetime.datetime.utcnow().strftime("%d/%m/%Y")
            due_date = (datetime.datetime.utcnow() + datetime.timedelta(days=7)).strftime("%d/%m/%Y")
            invoice = Invoice(
                order_ref=order_id,
                billing_info=billing_info,
                total_amount=order.total_amount,
                issue_date=issue_date,
                due_date=due_date,
                status="ISSUED",
            )
            async with Invoice.async_session() as inv_session:
                inv_session.add(invoice)
                await inv_session.commit()
            # Update order status
            order.status = OrderStatus.INVOICED
            order.invoice_ref = invoice.id
            order.updated_at = datetime.datetime.utcnow().isoformat()
            await session.commit()
        await wal.append_to_wal({"action": "create_invoice", "order_id": order_id, "invoice_id": invoice.id})
        return invoice
