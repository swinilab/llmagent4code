"""PaymentService – processes payments and verifies them.

Uses tenacity for retrying external gateway calls (NFR 2.2).
"""

import datetime
from decimal import Decimal

from tenacity import retry, stop_after_attempt, wait_fixed

from app.db.models import Payment, Order, OrderStatus, PaymentStatus, PaymentMethod
from app.persistence.wal import WAL

wal = WAL()

class PaymentService:
    async def process_payment(self, order_id: str):
        async with Order.async_session() as session:
            order = await session.get(Order, order_id)
            if not order:
                raise ValueError("Order not found")
            if order.status != OrderStatus.INVOICED:
                raise ValueError("Order must be INVOICED before payment")
            # Create payment record
            payment = Payment(
                order_ref=order_id,
                amount=order.total_amount,
                timestamp=datetime.datetime.utcnow().isoformat(),
                status=PaymentStatus.PENDING,
                method=PaymentMethod.CREDIT_CARD,
            )
            async with Payment.async_session() as pay_session:
                pay_session.add(payment)
                await pay_session.commit()
            # Simulate external gateway call with retry
            await self._call_gateway_with_retry(payment.id)
            # Upon success, update status
            payment.status = PaymentStatus.VERIFIED
            await pay_session.commit()
            # Update order status
            order.status = OrderStatus.PAID
            order.updated_at = datetime.datetime.utcnow().isoformat()
            await session.commit()
        await wal.append_to_wal({"action": "process_payment", "order_id": order_id, "payment_id": payment.id})
        return payment

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    async def _call_gateway_with_retry(self, payment_id: str):
        # Placeholder for real gateway integration – raise exception to trigger retry
        # For demo, we assume success.
        return True
