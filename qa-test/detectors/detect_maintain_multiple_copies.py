"""Maintain Multiple Copies of Computations (caching)."""

from .astutils import (PRESENT, WEAK, ABSENT, MISLOCATED,
                       has_decorator, calls_to, line_of, find_anchor_two_scope)


def detect(func_nodes, trees, src, entry):
    # ANCHOR 1: cache decorator must be on a CLAIMED function
    for fn in func_nodes:
        dec = has_decorator(fn, "cached", "cache", "lru_cache")
        if dec is not None:
            return PRESENT, f"cache decorator on {fn.name} @ line {line_of(dec)}"

    # ANCHOR 2: explicit cache read (.get) — two-scope
    def _finder(scope):
        for call in calls_to(scope, "get"):
            return call
        return None

    hit, where = find_anchor_two_scope(func_nodes, trees, _finder)
    if hit is not None:
        if where == "file":
            return MISLOCATED, "cache read (get) present in claimed file but not in a claimed function"
        return PRESENT, f"cache read (get) present @ line {line_of(hit)}"

    # writes only, no reads
    for fn in func_nodes:
        if any(True for _ in calls_to(fn, "set")):
            return WEAK, "cache write (set) but no read — cache never consulted"
    return ABSENT, "no cache decorator or get/set found in claimed surface"