"""Introduce Concurrency."""

from .astutils import (PRESENT, WEAK, ABSENT,
                       is_async, has_await, has_blocking_call,
                       calls_to, keyword_value, literal_int, line_of)


def detect(func_nodes, trees, src, entry):
    saw_async = False
    for fn in func_nodes:
        for call in calls_to(fn, "ThreadPoolExecutor", "ProcessPoolExecutor", "gather"):
            return PRESENT, f"concurrency primitive used @ line {line_of(call)}"
        for call in calls_to(fn, "run", "Config", "Server"):
            w = keyword_value(call, "workers")
            if w is not None:
                val = literal_int(w)
                if val is None:
                    return WEAK, f"workers=<non-literal> @ line {line_of(call)}"
                if val > 1:
                    return PRESENT, f"workers={val} @ line {line_of(call)}"
                return WEAK, f"workers={val} (single worker) @ line {line_of(call)}"
    for fn in func_nodes:
        if is_async(fn):
            saw_async = True
            if has_await(fn):
                return PRESENT, f"async def {fn.name} awaits I/O @ line {line_of(fn)}"
            if has_blocking_call(fn):
                return WEAK, f"async def {fn.name} blocking call, no await — fake async @ line {line_of(fn)}"
    if saw_async:
        return WEAK, "async def present but no await found — inconclusive"
    return ABSENT, "no async def, worker pool, or workers= in claimed functions"