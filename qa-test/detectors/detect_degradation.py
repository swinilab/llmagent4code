"""Degradation.

Anchor:        a 503 service-unavailable signal, in ANY of these forms:
                 - bare literal 503
                 - named constant HTTP_503_SERVICE_UNAVAILABLE (any attr with '503')
                 - status_code=503 keyword
                 - HTTPException(...503...) construction
Discriminator: the 503 is gated on a condition (inside an If).
Scope:         two-scope — enforcement often lives in a claimed service file
               rather than the flag-manager function, so file-scope => MISLOCATED.
"""

import ast
from .astutils import (PRESENT, WEAK, ABSENT, MISLOCATED,
                       dotted_name, line_of, find_anchor_two_scope)


def _is_503_node(node):
    # bare literal 503
    if isinstance(node, ast.Constant) and node.value == 503:
        return True
    # named constant e.g. status.HTTP_503_SERVICE_UNAVAILABLE
    if isinstance(node, ast.Attribute):
        name = node.attr.upper()
        if "503" in name or "SERVICE_UNAVAILABLE" in name:
            return True
    return False


def _find_503(scope):
    for node in ast.walk(scope):
        if _is_503_node(node):
            return node
    return None


def _503_inside_if(scope):
    for node in ast.walk(scope):
        if isinstance(node, ast.If):
            for sub in ast.walk(node):
                if _is_503_node(sub):
                    return line_of(sub)
    return None


def detect(func_nodes, trees, src, entry):
    hit, where = find_anchor_two_scope(func_nodes, trees, _find_503)
    if hit is None:
        return ABSENT, "no 503 degradation signal found in claimed surface"

    ln = line_of(hit)
    # discriminator: gated? check the scope the anchor was found in
    gated = None
    if where == "function":
        for fn in func_nodes:
            g = _503_inside_if(fn)
            if g is not None:
                gated = g
                break
    else:
        for tree in trees:
            g = _503_inside_if(tree)
            if g is not None:
                gated = g
                break

    if where == "file":
        note = "gated" if gated else "ungated"
        return MISLOCATED, (f"503 ({note}) present in claimed file but not in a claimed "
                            f"function @ line {ln}")
    if gated is not None:
        return PRESENT, f"conditional 503 (gated) @ line {gated}"
    return WEAK, f"503 present but not inside a conditional @ line {ln}"