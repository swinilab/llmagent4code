"""Quick test to verify OMS code works."""
import sys
sys.path.insert(0, 'oms')

from app.infrastructure import recover_pending_orders, CircuitBreaker, CircuitBreakerError
from app.models import init_db, engine
from sqlalchemy.orm import Session, sessionmaker

init_db()
s = sessionmaker(bind=engine)()
try:
    result = recover_pending_orders(s)
    print('recover_pending_orders result:', result)
finally:
    s.close()

# Test circuit breaker
cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=0.1)
assert cb.state == "CLOSED"

# Test that business-logic exceptions (ValueError) do NOT count toward the breaker
try:
    cb.call(lambda: (_ for _ in ()).throw(ValueError("invalid state transition")))
except ValueError:
    pass
assert cb.state == "CLOSED"  # Still CLOSED - ValueError does not count

try:
    cb.call(lambda: (_ for _ in ()).throw(ValueError("another bad request")))
except ValueError:
    pass
assert cb.state == "CLOSED"  # Still CLOSED - ValueError does not count

# Test that infrastructure-level exceptions (ConnectionError) DO count toward the breaker
try:
    cb.call(lambda: (_ for _ in ()).throw(ConnectionError("DB connection refused")))
except ConnectionError:
    pass
assert cb.state == "CLOSED"  # Only 1 infrastructure failure, threshold is 2

try:
    cb.call(lambda: (_ for _ in ()).throw(ConnectionError("DB timeout")))
except ConnectionError:
    pass
assert cb.state == "OPEN"  # 2 infrastructure failures, threshold reached

# Verify CircuitBreakerError is raised when circuit is open
try:
    cb.call(lambda: "should not execute")
    assert False, "Expected CircuitBreakerError"
except CircuitBreakerError:
    pass

print("All tests passed!")
