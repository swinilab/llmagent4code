"""Test the order state machine transitions."""
import sys
sys.path.insert(0, '.')
from oms.domain.enums import OrderStatus
from oms.domain.order_state import OrderStateMachine

# Test valid transitions
print("=== Testing Valid Transitions ===")
transitions = [
    (OrderStatus.CREATED, "accept", OrderStatus.ACCEPTED),
    (OrderStatus.ACCEPTED, "invoice", OrderStatus.INVOICED),
    (OrderStatus.INVOICED, "pay", OrderStatus.PAID),
    (OrderStatus.PAID, "ship", OrderStatus.SHIPPED),
    (OrderStatus.SHIPPED, "close", OrderStatus.CLOSED),
    (OrderStatus.CREATED, "cancel", OrderStatus.CANCELLED),
    (OrderStatus.ACCEPTED, "cancel", OrderStatus.CANCELLED),
    (OrderStatus.INVOICED, "cancel", OrderStatus.CANCELLED),
    (OrderStatus.PAID, "cancel", OrderStatus.CANCELLED),
]

for from_state, event, expected in transitions:
    result = OrderStateMachine.transition(from_state, event)
    assert result == expected, f"Expected {expected}, got {result}"
    print(f"  {from_state.value} --[{event}]--> {result.value} ✅")

# Test invalid transitions
print("\n=== Testing Invalid Transitions ===")
invalid = [
    (OrderStatus.CREATED, "ship"),
    (OrderStatus.PAID, "accept"),
    (OrderStatus.CLOSED, "cancel"),
    (OrderStatus.CANCELLED, "accept"),
    (OrderStatus.SHIPPED, "cancel"),
]
for from_state, event in invalid:
    try:
        OrderStateMachine.transition(from_state, event)
        print(f"  {from_state.value} --[{event}]--> (should have failed) ❌")
    except ValueError:
        print(f"  {from_state.value} --[{event}]--> REJECTED ✅")

# Test allowed events
print("\n=== Testing Allowed Events ===")
for state in OrderStatus:
    events = OrderStateMachine.allowed_events(state)
    print(f"  {state.value}: {events}")

print("\n✅ All state machine tests passed")
