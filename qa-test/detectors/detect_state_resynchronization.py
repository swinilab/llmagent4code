"""State Resynchronization.

Anchor:        a persisted-state READ (open/read/fetch/execute) in a claimed fn.
Discriminator: the reading function is invoked (wired to startup) somewhere in
               the claimed surface (any claimed tree), not merely defined.
Scope:         anchor is function-scoped; the 'is it called' wiring check is
               searched across ALL claimed trees (so a startup call in a claimed
               main.py counts).
"""

import ast
from .astutils import (PRESENT, WEAK, ABSENT, calls_to, dotted_name, line_of)

READ_CALLS = ("open", "read", "readline", "readlines", "fetchall", "fetchone", "execute")


def _has_read(fn):
    for call in calls_to(fn, *READ_CALLS):
        return line_of(call)
    return None


def _called_in_trees(trees, func_name, own_fn):
    """True if func_name is called anywhere in the claimed trees, excluding the
    call sites inside its own definition body."""
    own_range = range(getattr(own_fn, "lineno", 0), getattr(own_fn, "end_lineno", 0) + 1)
    for tree in trees:
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                dn = dotted_name(node.func)
                last = dn.split(".")[-1] if dn else ""
                if last == func_name and getattr(node, "lineno", -1) not in own_range:
                    return True
    return False


def detect(func_nodes, trees, src, entry):
    # Prefer a function that both READS state and looks like a replay/restore
    candidates = sorted(
        func_nodes,
        key=lambda fn: 0 if any(w in fn.name.lower()
                                for w in ("replay", "restore", "recover", "resync", "startup"))
        else 1,
    )
    for fn in candidates:
        ln = _has_read(fn)
        if ln is None:
            continue
        if _called_in_trees(trees, fn.name, fn):
            return PRESENT, f"{fn.name} reads persisted state @ line {ln} and is invoked at startup"
        return WEAK, f"{fn.name} reads persisted state @ line {ln} but is never called (dead recovery)"
    return ABSENT, "no persisted-state read found in claimed functions"