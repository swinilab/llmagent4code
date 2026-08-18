"""
Invoice service with business logic and validation
Implements NFR 2.4 Transactions via ACID database operations
"""
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from oms.repository.invoice_repository import InvoiceRepository
from oms.repository.order_repository import OrderRepository
from oms.repository.customer_repository import CustomerRepository
from oms.domain.models import Invoice, InvoiceCreate, InvoiceStatus, OrderStatus
from oms.infrastructure.exceptions import NotFoundException, ConflictException
from oms.infrastructure.cache.memory_cache import MemoryCache
from oms.infrastructure.database import transaction_session


class InvoiceService:
    """
    Invoice service implementing business logic
    Implements NFR 2.4 via transactional semantics
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = InvoiceRepository(session)
        self.order_repo = OrderRepository(session)
        self.customer_repo = CustomerRepository(session)
        self.cache = MemoryCache.get_instance()
    
    async def get_by_id(self, invoice_id: str) -> Invoice:
        """Get invoice by ID with cache lookup"""
        # Try cache first (NFR 1.2)
        cached = await self.cache.get(f"invoice:{invoice_id}")
        if cached:
            return Invoice(**cached)
        
        # Fallback to database
        invoice = await self.repository.get_by_id(invoice_id)
        if not invoice:
            raise NotFoundException(f"Invoice {invoice_id} not found")
        
        # Populate cache
        await self.cache.set(f"invoice:{invoice_id}", invoice.model_dump())
        return invoice
    
    async def get_all(self) -> List[Invoice]:
        """Get all invoices"""
        return await self.repository.get_all()
    
    async def get_by_order(self, order_id: str) -> Invoice:
        """Get invoice by order ID"""
        invoice = await self.repository.get_by_order(order_id)
        if not invoice:
            raise NotFoundException(f"Invoice for order {order_id} not found")
        return invoice
    
    async def create(self, invoice: InvoiceCreate) -> Invoice:
        """
        Create new invoice with validation
        NFR 2.4: Transaction ensures atomicity and consistency
        """
        async with transaction_session() as session:
            # Create repositories with the transaction session
            invoice_repo = InvoiceRepository(session)
            order_repo = OrderRepository(session)
            customer_repo = CustomerRepository(session)
            
            # Validate order exists and is in ACCEPTED state
            order = await order_repo.get_by_id(invoice.orderRef)
            if not order:
                raise NotFoundException(f"Order {invoice.orderRef} not found")
            
            if OrderStatus(order.status) != OrderStatus.ACCEPTED:
                raise ConflictException(
                    f"Order must be ACCEPTED to create invoice, current status: {order.status}"
                )
            
            # Check invoice doesn't already exist
            existing = await invoice_repo.get_by_order(invoice.orderRef)
            if existing:
                raise ConflictException(f"Invoice already exists for order {invoice.orderRef}")
            
            # Get customer for billing info snapshot
            customer = await customer_repo.get_by_id(order.customerRef)
            if not customer:
                raise NotFoundException(f"Customer {order.customerRef} not found")
            
            # Determine issue date and due date
            if invoice.issueDate:
                issue_date = invoice.issueDate
            else:
                issue_date = datetime.now(timezone.utc).strftime("%d/%m/%Y")
            
            if invoice.dueDate:
                due_date = invoice.dueDate
            else:
                # Default: issue date + 7 days
                issue_dt = datetime.strptime(issue_date, "%d/%m/%Y")
                due_dt = issue_dt + timedelta(days=7)
                due_date = due_dt.strftime("%d/%m/%Y")
            
            # Validate due date >= issue date
            issue_dt = datetime.strptime(issue_date, "%d/%m/%Y")
            due_dt = datetime.strptime(due_date, "%d/%m/%Y")
            if due_dt < issue_dt:
                raise ConflictException("Due date must be >= issue date")
            
            # Create invoice
            created = await invoice_repo.create(
                order_ref=invoice.orderRef,
                billing_name=customer.name,
                billing_address=customer.address,
                total_amount=order.totalAmount,
                issue_date=issue_date,
                due_date=due_date
            )
            
            # Update order with invoice reference
            await order_repo.set_invoice_ref(invoice.orderRef, created.id)
            
            # Update order status to INVOICED
            await order_repo.update_status(invoice.orderRef, OrderStatus.INVOICED)
            
            # Populate cache
            await self.cache.set(f"invoice:{created.id}", created.model_dump())
            await self.cache.delete(f"order:{invoice.orderRef}")
            
            return created
    
    async def update_status(self, invoice_id: str, new_status: InvoiceStatus) -> Invoice:
        """Update invoice status"""
        async with transaction_session() as session:
            # Create repository with the transaction session
            invoice_repo = InvoiceRepository(session)
            
            invoice = await invoice_repo.get_by_id(invoice_id)
            if not invoice:
                raise NotFoundException(f"Invoice {invoice_id} not found")
            
            # Validate status transition
            valid_transitions = {
                InvoiceStatus.ISSUED: [InvoiceStatus.PAID, InvoiceStatus.OVERDUE, InvoiceStatus.CANCELLED],
                InvoiceStatus.PAID: [],
                InvoiceStatus.OVERDUE: [InvoiceStatus.PAID, InvoiceStatus.CANCELLED],
                InvoiceStatus.CANCELLED: []
            }
            
            current_status = InvoiceStatus(invoice.status)
            if new_status not in valid_transitions.get(current_status, []):
                raise ConflictException(
                    f"Invalid status transition from {current_status.value} to {new_status.value}"
                )
            
            updated = await invoice_repo.update_status(invoice_id, new_status)
            
            # Invalidate cache
            await self.cache.delete(f"invoice:{invoice_id}")
            
            return updated
    
    async def delete(self, invoice_id: str) -> bool:
        """Delete invoice"""
        invoice = await self.repository.get_by_id(invoice_id)
        if not invoice:
            return False
        
        # Invalidate cache
        await self.cache.delete(f"invoice:{invoice_id}")
        
        return await self.repository.delete(invoice_id)
