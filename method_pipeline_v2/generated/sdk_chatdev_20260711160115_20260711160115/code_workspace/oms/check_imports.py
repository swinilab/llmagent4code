"""Quick import check."""
import sys
sys.path.insert(0, '.')
from oms.domain.enums import OrderStatus
print('Domain enums OK')
from oms.domain.order_state import OrderStateMachine
print('State machine OK')
from oms.domain.models import Order, Customer, Product, Payment, Invoice
print('Domain models OK')
from oms.config import settings
print('Config OK')
print('All imports successful')
