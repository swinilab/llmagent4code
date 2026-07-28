"""Retry."""

import ast
from .astutils import (PRESENT, WEAK, ABSENT, has_decorator, dotted_name, line_of)


def _retry_decorator_has_stop(dec):
    if not isinstance(dec, ast.Call):
        return False
    for kw in dec.keywords:
        if kw.arg and ("stop" in kw.arg or "max" in kw.arg or "attempt" in kw.arg):
            return True
    for arg in dec.args:
        if isinstance(arg, ast.Call) and "stop" in dotted_name(arg.func).lower():
            return True
    return False


def _bounded_loop_with_try(fn):
    for node in ast.walk(fn):
        if isinstance(node, ast.For):
            if any(isinstance(s, ast.Try) for s in ast.walk(node)):
                return line_of(node), True
        if isinstance(node, ast.While):
            if not any(isinstance(s, ast.Try) for s in ast.walk(node)):
                continue
            has_break = any(isinstance(s, ast.Break) for s in ast.walk(node))
            return line_of(node), has_break
    return None, False


def detect(func_nodes, trees, src, entry):
    for fn in func_nodes:
        dec = has_decorator(fn, "retry")
        if dec is not None:
            if _retry_decorator_has_stop(dec):
                return PRESENT, f"@retry with stop condition on {fn.name} @ line {line_of(dec)}"
            return WEAK, f"bare @retry (no stop) on {fn.name} @ line {line_of(dec)}"
        ln, bounded = _bounded_loop_with_try(fn)
        if ln is not None:
            if bounded:
                return PRESENT, f"bounded retry loop @ line {ln}"
            return WEAK, f"retry loop with no clear stop/break @ line {ln}"
    return ABSENT, "no @retry decorator or retry loop in claimed functions"