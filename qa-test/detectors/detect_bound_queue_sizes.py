"""Bound Queue Sizes.

Anchor:        a Queue(...) construction.
Discriminator: maxsize keyword is a positive integer literal.
Scope:         two-scope — construction usually at module/file level, so if it
               is not inside a claimed function, report MISLOCATED.
"""

from .astutils import (PRESENT, WEAK, ABSENT, MISLOCATED,
                       calls_to, keyword_value, literal_int, line_of,
                       find_anchor_two_scope)


def _first_queue_call(scope):
    for call in calls_to(scope, "Queue"):
        return call
    return None


def detect(func_nodes, trees, src, entry):
    call, where = find_anchor_two_scope(func_nodes, trees, _first_queue_call)
    if call is None:
        return ABSENT, "no Queue(...) construction found in claimed surface"
    ln = line_of(call)
    maxsize = keyword_value(call, "maxsize")
    if maxsize is None:
        return ABSENT, f"Queue() with no maxsize (unbounded) @ line {ln}"
    val = literal_int(maxsize)
    if val is None:
        return WEAK, f"Queue(maxsize=<non-literal>) @ line {ln} — cannot resolve statically"
    if val <= 0:
        return ABSENT, f"Queue(maxsize={val}) — non-positive means unbounded @ line {ln}"
    if where == "file":
        return MISLOCATED, (f"Queue(maxsize={val}) @ line {ln} — bounded, but constructed "
                            f"outside the claimed functions")
    return PRESENT, f"Queue(maxsize={val}) @ line {ln}"