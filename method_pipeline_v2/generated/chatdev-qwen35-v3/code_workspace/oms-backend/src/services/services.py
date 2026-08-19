import threading
from typing import Optional, List
from datetime import datetime
from src.models import Customer, Product, Order, Payment, Invoice, OrderStatus, PaymentStatus, InvoiceStatus
from src.repositories import (
    CustomerRepository,
    ProductRepository,
    OrderRepository,
    PaymentRepository,
    InvoiceRepository,
)


class RateLimiter:
    """Rate limiter for NFR 1.1 - Limit Event Response."""
    
    def __init__(self, max_events: int = 100, window_seconds: int = 60):
        self.max_events = max_events
        self.window_seconds = window_seconds
        self._events: List[float] = []
        self._lock = threading.Lock()
    
    def acquire(self) -> bool:
        """Try to acquire a rate limit slot. Returns True if allowed, False if rate limited."""
        with self._lock:
            now = datetime.utcnow().timestamp()
            cutoff = now - self.window_seconds
            
            # Remove old events outside the window
            self._events = [t for t in self._events if t > cutoff]
            
            if len(self._events) >= self.max_events:
                return False
            
            self._events.append(now)
            return True


class CustomerService:
    def __init__(self, repo: CustomerRepository, rate_limiter: Optional[RateLimiter] = None):
        self.repo = repo
        self.rate_limiter = rate_limiter or RateLimiter()
    
    def create_customer(self, customer: Customer) -> Customer:
        """Create a new customer with rate limiting."""
        if not self.rate_limiter.acquire():
            raise Exception("Rate limit exceeded")
        return self.repo.save(customer)
    
    def get_customer(self, customer_id: str) -> Optional[Customer]:
        """Get customer by ID."""
        return self.repo.find_by_id(customer_id)
    
    def get_all_customers(self) -> List[Customer]:
        """Get all customers."""
        return self.repo.find_all()
    
    def add_to_order_history(self, customer_id: str, order_id: str) -> bool:
        """Add order to customer's order history."""
        customer = self.repo.find_by_id(customer_id)
        if not customer:
            return False
        
        # Soft cap of 10,000 orders
        if len(customer.orderHistory) >= 10000:
            return False
        
        customer.orderHistory.append(order_id)
        self.repo.save(customer)
        return True


class ProductService:
    def __init__(self, repo: ProductRepository, rate_limiter: Optional[RateLimiter] = None):
        self.repo = repo
        self.rate_limiter = rate_limiter or RateLimiter()
    
    def create_product(self, product: Product) -> Product:
        """Create a new product with rate limiting."""
        if not self.rate_limiter.acquire():
            raise Exception("Rate limit exceeded")
        return self.repo.save(product)
    
    def get_product(self, product_id: str) -> Optional[Product]:
        """Get product by ID."""
        return self.repo.find_by_id(product_id)
    
    def get_all_products(self) -> List[Product]:
        """Get all products."""
        return self.repo.find_all()


class OrderService:
    def __init__(
        self,
        order_repo: OrderRepository,
        customer_repo: CustomerRepository,
        product_repo: ProductRepository,
        rate_limiter: Optional[RateLimiter] = None,
    ):
        self.order_repo = order_repo
        self.customer_repo = customer_repo
        self.product_repo = product_repo
        self.rate_limiter = rate_limiter or RateLimiter()
    
    def create_order(self, order: Order) -> Order:
        """Create a new order with validation and rate limiting."""
        if not self.rate_limiter.acquire():
            raise Exception("Rate limit exceeded")
        
        # Validate customerRef exists
        customer = self.customer_repo.find_by_id(order.customerRef)
        if not customer:
            raise ValueError(f"Customer {order.customerRef} not found")
        
        # Validate each line item's productRef exists and compute unitPriceSnapshot
        for item in order.lineItems:
            product = self.product_repo.find_by_id(item.productRef)
            if not product:
                raise ValueError(f"Product {item.productRef} not found")
            
            # Server-compute unitPriceSnapshot from product price
            item.unitPriceSnapshot = product.price.amount
        
        # Server-compute totalAmount
        computed_total = sum(item.quantity * float(item.unitPriceSnapshot) for item in order.lineItems)
        order.totalAmount = f"{computed_total:.2f}"
        
        # Set initial status
        order.status = OrderStatus.PLACED
        
        saved_order = self.order_repo.save(order)
        
        # Add to customer's order history
        self.customer_repo.find_by_id(order.customerRef)
        CustomerService(self.customer_repo).add_to_order_history(order.customerRef, order.id)
        
        return saved_order
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID."""
        return self.order_repo.find_by_id(order_id)
    
    def get_all_orders(self) -> List[Order]:
        """Get all orders."""
        return self.order_repo.find_all()
    
    def accept_order(self, order_id: str) -> Order:
        """Accept an order (Order Staff action)."""
        order = self.order_repo.find_by_id(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        if order.status != OrderStatus.PLACED:
            raise ValueError(f"Order must be in PLACED status, currently {order.status.value}")
        
        order.status = OrderStatus.ACCEPTED
        order.updatedAt = datetime.utcnow().isoformat() + "Z"
        return self.order_repo.save(order)
    
    def ship_order(self, order_id: str) -> Order:
        """Ship an order (Order Staff action)."""
        order = self.order_repo.find_by_id(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        if order.status != OrderStatus.PAID:
            raise ValueError(f"Order must be in PAID status, currently {order.status.value}")
        
        order.status = OrderStatus.SHIPPED
        order.updatedAt = datetime.utcnow().isoformat() + "Z"
        return self.order_repo.save(order)
    
    def close_order(self, order_id: str) -> Order:
        """Close an order (Order Staff action)."""
        order = self.order_repo.find_by_id(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        if order.status != OrderStatus.SHIPPED:
            raise ValueError(f"Order must be in SHIPPED status, currently {order.status.value}")
        
        order.status = OrderStatus.CLOSED
        order.updatedAt = datetime.utcnow().isoformat() + "Z"
        return self.order_repo.save(order)
    
    def cancel_order(self, order_id: str) -> Order:
        """Cancel an order."""
        order = self.order_repo.find_by_id(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        if order.status not in [OrderStatus.PLACED, OrderStatus.ACCEPTED]:
            raise ValueError(f"Order can only be cancelled in PLACED or ACCEPTED status, currently {order.status.value}")
        
        order.status = OrderStatus.CANCELLED
        order.updatedAt = datetime.utcnow().isoformat() + "Z"
        return self.order_repo.save(order)


class InvoiceService:
    def __init__(
        self,
        invoice_repo: InvoiceRepository,
        order_repo: OrderRepository,
        customer_repo: CustomerRepository,
        rate_limiter: Optional[RateLimiter] = None,
    ):
        self.invoice_repo = invoice_repo
        self.order_repo = order_repo
        self.customer_repo = customer_repo
        self.rate_limiter = rate_limiter or RateLimiter()
    
    def create_invoice(self, invoice: Invoice) -> Invoice:
        """Create an invoice for an accepted order (Accountant action)."""
        if not self.rate_limiter.acquire():
            raise Exception("Rate limit exceeded")
        
        # Validate order exists and is in ACCEPTED status
        order = self.order_repo.find_by_id(invoice.orderRef)
        if not order:
            raise ValueError(f"Order {invoice.orderRef} not found")
        
        if order.status != OrderStatus.ACCEPTED:
            raise ValueError(f"Order must be in ACCEPTED status, currently {order.status.value}")
        
        # Check invoice doesn't already exist for this order
        existing = self.invoice_repo.find_by_order_ref(invoice.orderRef)
        if existing:
            raise ValueError(f"Invoice already exists for order {invoice.orderRef}")
        
        # Server-copy billing info from customer
        customer = self.customer_repo.find_by_id(order.customerRef)
        if not customer:
            raise ValueError(f"Customer {order.customerRef} not found")
        
        invoice.billingInfo.name = customer.name
        invoice.billingInfo.address = customer.address
        
        # Server-set totalAmount from order
        invoice.totalAmount = order.totalAmount
        
        # Set default dates if not provided
        if not invoice.issueDate:
            invoice.issueDate = datetime.utcnow().strftime("%d/%m/%Y")
        if not invoice.dueDate:
            from datetime import timedelta
            invoice.dueDate = (datetime.utcnow() + timedelta(days=7)).strftime("%d/%m/%Y")
        
        invoice.status = InvoiceStatus.ISSUED
        
        saved_invoice = self.invoice_repo.save(invoice)
        
        # Update order with invoiceRef
        self.order_repo.set_invoice_ref(order.id, invoice.id)
        self.order_repo.update_status(order.id, OrderStatus.INVOICED.value)
        
        return saved_invoice
    
    def get_invoice(self, invoice_id: str) -> Optional[Invoice]:
        """Get invoice by ID."""
        return self.invoice_repo.find_by_id(invoice_id)
    
    def get_all_invoices(self) -> List[Invoice]:
        """Get all invoices."""
        return self.invoice_repo.find_all()
    
    def get_invoice_by_order_ref(self, order_id: str) -> Optional[Invoice]:
        """Get invoice by order reference."""
        return self.invoice_repo.find_by_order_ref(order_id)


class PaymentService:
    def __init__(
        self,
        payment_repo: PaymentRepository,
        order_repo: OrderRepository,
        invoice_repo: InvoiceRepository,
        rate_limiter: Optional[RateLimiter] = None,
    ):
        self.payment_repo = payment_repo
        self.order_repo = order_repo
        self.invoice_repo = invoice_repo
        self.rate_limiter = rate_limiter or RateLimiter()
    
    def create_payment(self, payment: Payment) -> Payment:
        """Create a payment for an invoiced order (Customer action)."""
        if not self.rate_limiter.acquire():
            raise Exception("Rate limit exceeded")
        
        # Validate order exists and is in INVOICED status
        order = self.order_repo.find_by_id(payment.orderRef)
        if not order:
            raise ValueError(f"Order {payment.orderRef} not found")
        
        if order.status != OrderStatus.INVOICED:
            raise ValueError(f"Order must be in INVOICED status, currently {order.status.value}")
        
        # Get invoice and validate amount
        invoice = self.invoice_repo.find_by_order_ref(payment.orderRef)
        if not invoice:
            raise ValueError(f"No invoice found for order {payment.orderRef}")
        
        # Validate payment amount equals invoice totalAmount
        if payment.amount != invoice.totalAmount:
            raise ValueError(f"Payment amount {payment.amount} must equal invoice total {invoice.totalAmount}")
        
        payment.status = PaymentStatus.PENDING
        payment.timestamp = datetime.utcnow().isoformat() + "Z"
        
        return self.payment_repo.save(payment)
    
    def get_payment(self, payment_id: str) -> Optional[Payment]:
        """Get payment by ID."""
        return self.payment_repo.find_by_id(payment_id)
    
    def get_all_payments(self) -> List[Payment]:
        """Get all payments."""
        return self.payment_repo.find_all()
    
    def verify_payment(self, payment_id: str) -> Payment:
        """Verify a payment (Accountant action)."""
        payment = self.payment_repo.find_by_id(payment_id)
        if not payment:
            raise ValueError(f"Payment {payment_id} not found")
        
        if payment.status != PaymentStatus.PENDING:
            raise ValueError(f"Payment must be in PENDING status, currently {payment.status.value}")
        
        payment.status = PaymentStatus.VERIFIED
        payment.timestamp = datetime.utcnow().isoformat() + "Z"
        saved_payment = self.payment_repo.save(payment)
        
        # Update order status to PAID
        self.order_repo.update_status(payment.orderRef, OrderStatus.PAID.value)
        
        # Update invoice status to PAID
        invoice = self.invoice_repo.find_by_order_ref(payment.orderRef)
        if invoice:
            invoice.status = InvoiceStatus.PAID
            self.invoice_repo.save(invoice)
        
        return saved_payment
    
    def reject_payment(self, payment_id: str) -> Payment:
        """Reject a payment (Accountant action)."""
        payment = self.payment_repo.find_by_id(payment_id)
        if not payment:
            raise ValueError(f"Payment {payment_id} not found")
        
        if payment.status != PaymentStatus.PENDING:
            raise ValueError(f"Payment must be in PENDING status, currently {payment.status.value}")
        
        payment.status = PaymentStatus.REJECTED
        payment.timestamp = datetime.utcnow().isoformat() + "Z"
        return self.payment_repo.save(payment)
