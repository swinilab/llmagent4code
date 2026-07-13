import random
import time
from typing import Dict, Any

class PaymentGateway:
    """
    Simulates an external payment processor.
    Randomly fails to simulate network issues or gateway downtime.
    """
    def __init__(self, failure_rate: float = 0.1):
        self.failure_rate = failure_rate  # probability of failure

    def charge(self, amount: int, method: str) -> Dict[str, Any]:
        """
        Attempt to charge the given amount using the specified method.
        Returns a dictionary with transaction details if successful.
        Raises an exception if the transaction fails.
        """
        # Simulate network latency
        time.sleep(0.05)
        
        if random.random() < self.failure_rate:
            raise Exception("Payment gateway unavailable or transaction declined")
        
        # Simulate successful transaction
        return {
            "transaction_id": f"txn_{int(time.time() * 1000)}",
            "amount": amount,
            "method": method,
            "status": "captured",
            "timestamp": time.time(),
        }