"""
Test the circuit breaker fix: business-logic exceptions in HALF_OPEN state
must NOT consume probe slots (the _half_open_requests counter leak bug).
"""
import sys
sys.path.insert(0, 'oms')

from app.infrastructure import CircuitBreaker, CircuitBreakerError
import time


def test_business_logic_never_counts_toward_failure_threshold():
    """Business-logic exceptions must never increment failure_count."""
    cb = CircuitBreaker("test_biz_logic", failure_threshold=5, recovery_timeout=30.0)

    for i in range(10):
        try:
            cb.call(lambda: (_ for _ in ()).throw(ValueError("bad request")))
        except ValueError:
            pass
        assert cb.state == "CLOSED", f"Expected CLOSED after biz-exception #{i+1}, got {cb.state}"

    print("PASS: test_business_logic_never_counts_toward_failure_threshold")


def test_half_open_biz_errors_do_not_consume_probes():
    """
    Business-logic exceptions in HALF_OPEN must NOT consume probe slots.
    After N business-logic errors, a successful call should still close the circuit.
    This is the regression test for the _half_open_requests counter leak bug.
    """
    cb = CircuitBreaker("test_half_open_biz", failure_threshold=2, recovery_timeout=0.05, half_open_max_requests=3)

    # 1. Open the circuit with 2 infrastructure failures
    for i in range(2):
        try:
            cb.call(lambda: (_ for _ in ()).throw(ConnectionError("infra fail")))
        except ConnectionError:
            pass
    assert cb.state == "OPEN"

    # 2. Wait for recovery timeout
    time.sleep(0.06)

    # 3. Fire 3 business-logic exceptions in HALF_OPEN
    # Each one should be decremented back, so _half_open_requests stays at 0
    for i in range(3):
        try:
            cb.call(lambda: (_ for _ in ()).throw(ValueError("biz error")))
        except ValueError:
            pass
        assert cb.state == "HALF_OPEN", f"Expected HALF_OPEN after biz-exception #{i+1}, got {cb.state}"

    # 4. A successful call should close the circuit
    result = cb.call(lambda: "success")
    assert result == "success"
    assert cb.state == "CLOSED", f"Expected CLOSED after success, got {cb.state}"

    print("PASS: test_half_open_biz_errors_do_not_consume_probes")


def test_half_open_infra_failure_reopens_circuit():
    """
    An infrastructure failure in HALF_OPEN increments _failure_count.
    If _failure_count reaches the threshold, the circuit re-opens.
    """
    cb = CircuitBreaker("test_half_open_infra", failure_threshold=2, recovery_timeout=0.05, half_open_max_requests=3)

    # Open the circuit
    for i in range(2):
        try:
            cb.call(lambda: (_ for _ in ()).throw(ConnectionError("infra fail")))
        except ConnectionError:
            pass
    assert cb.state == "OPEN"

    # Wait for recovery
    time.sleep(0.06)

    # First infra failure in HALF_OPEN: _failure_count becomes 3 >= 2, circuit re-opens
    try:
        cb.call(lambda: (_ for _ in ()).throw(ConnectionError("infra in half-open")))
    except ConnectionError:
        pass
    assert cb.state == "OPEN", f"Expected OPEN after infra failure in HALF_OPEN, got {cb.state}"

    print("PASS: test_half_open_infra_failure_reopens_circuit")


def test_mixed_exceptions_in_half_open():
    """
    Mix of business-logic and infrastructure exceptions in HALF_OPEN.
    Only infra failures should affect the circuit state.
    """
    cb = CircuitBreaker("test_mixed", failure_threshold=2, recovery_timeout=0.05, half_open_max_requests=3)

    # Open the circuit
    for i in range(2):
        try:
            cb.call(lambda: (_ for _ in ()).throw(ConnectionError("infra fail")))
        except ConnectionError:
            pass
    assert cb.state == "OPEN"

    # Wait for recovery
    time.sleep(0.06)

    # Biz error - should NOT affect circuit state
    try:
        cb.call(lambda: (_ for _ in ()).throw(ValueError("biz error")))
    except ValueError:
        pass
    assert cb.state == "HALF_OPEN"

    # Another biz error - still HALF_OPEN
    try:
        cb.call(lambda: (_ for _ in ()).throw(ValueError("biz error 2")))
    except ValueError:
        pass
    assert cb.state == "HALF_OPEN"

    # Infra error - SHOULD re-open the circuit (_failure_count reaches threshold)
    try:
        cb.call(lambda: (_ for _ in ()).throw(ConnectionError("infra error")))
    except ConnectionError:
        pass
    assert cb.state == "OPEN", f"Expected OPEN after infra failure, got {cb.state}"

    print("PASS: test_mixed_exceptions_in_half_open")


if __name__ == "__main__":
    test_business_logic_never_counts_toward_failure_threshold()
    test_half_open_biz_errors_do_not_consume_probes()
    test_half_open_infra_failure_reopens_circuit()
    test_mixed_exceptions_in_half_open()
    print("\nAll circuit breaker fix tests passed!")
