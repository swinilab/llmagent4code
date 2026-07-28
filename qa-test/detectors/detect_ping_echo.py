"""Ping/Echo (health / liveness probe)."""

import ast
from .astutils import PRESENT, WEAK, ABSENT, line_of

HEALTH_WORDS = ("health", "live", "ready", "ping", "echo")


def _looks_health(name):
    n = (name or "").lower()
    return any(w in n for w in HEALTH_WORDS)


def _route_path_mentions_health(func_node):
    for dec in getattr(func_node, "decorator_list", []):
        if isinstance(dec, ast.Call):
            for arg in dec.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str) \
                        and _looks_health(arg.value):
                    return arg.value
    return None


def _body_only_returns_constant(func_node):
    for node in ast.walk(func_node):
        if isinstance(node, ast.Call):
            return False
        if isinstance(node, ast.If):
            return False
    return True


def detect(func_nodes, trees, src, entry):
    for fn in func_nodes:
        anchor = _looks_health(fn.name) or _route_path_mentions_health(fn)
        if not anchor:
            continue
        ln = line_of(fn)
        if _body_only_returns_constant(fn):
            return WEAK, f"health fn {fn.name} returns constant only, no probe @ line {ln}"
        return PRESENT, f"health probe {fn.name} performs a check @ line {ln}"
    return ABSENT, "no health/liveness/ping function found in claimed functions"