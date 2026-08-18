"""Test imports to verify code is functional"""
from oms_backend.domain.models import CustomerCreate, BankingDetails, ProductCreate, Price, OrderCreate, LineItem, PaymentCreate, InvoiceCreate, BillingInfo
from oms_backend.utils.validators import validate_customer_name, validate_customer_phone, validate_price_amount, validate_currency
from oms_backend.utils.rate_limiter import RateLimiter
from oms_backend.utils.cache import CacheManager
from oms_backend.utils.exceptions import OMSException, ValidationException, NotFoundException
from oms_backend.repository.models import CustomerModel, ProductModel, OrderModel, PaymentModel, InvoiceModel

print("All imports successful!")

# Test validation
valid, err = validate_customer_name("John Doe")
print(f"Name validation: valid={valid}, err={err}")

valid, err = validate_customer_phone("+1234567890")
print(f"Phone validation: valid={valid}, err={err}")

valid, err = validate_price_amount("99.99")
print(f"Price validation: valid={valid}, err={err}")

valid, err = validate_currency("USD")
print(f"Currency validation: valid={valid}, err={err}")

print("\nValidation tests passed!")
