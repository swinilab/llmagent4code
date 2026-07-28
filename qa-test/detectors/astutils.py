"""Shared AST helpers for tactic detectors.

Verdict labels are re-exported so every detector uses the same strings.
Each detector returns (status, evidence) where status is one of these three.
"""

import ast

PRESENT = "PRESENT"   # anchor found AND discriminator confirms it is real
WEAK = "WEAK"         # anchor found but discriminator cannot be resolved statically
ABSENT = "ABSENT"     # no anchor, or discriminator proves it is hollow
MISLOCATED = "MISLOCATED"  # anchor present in a claimed file but NOT in a claimed function


def dotted_name(node):
    """Best-effort dotted name of a call target.
    ast.Name -> 'Queue'; ast.Attribute -> 'asyncio.Queue'."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = dotted_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return ""


def calls_to(scope, *names):
    """Yield ast.Call nodes within `scope` whose target's dotted name ends with
    any of `names`. Matching on the last segment lets 'Queue' match
    'asyncio.Queue', 'queue.Queue', etc."""
    wanted = set(names)
    for node in ast.walk(scope):
        if isinstance(node, ast.Call):
            dn = dotted_name(node.func)
            last = dn.split(".")[-1] if dn else ""
            if last in wanted or dn in wanted:
                yield node


def keyword_value(call, argname):
    """Return the ast node for a keyword argument, or None if absent."""
    for kw in call.keywords:
        if kw.arg == argname:
            return kw.value
    return None


def literal_int(node):
    """If node is an int literal, return its value; else None."""
    if isinstance(node, ast.Constant) and isinstance(node.value, int) \
            and not isinstance(node.value, bool):
        return node.value
    return None


def has_decorator(func_node, *names):
    """Return the matching decorator node if func_node carries a decorator whose
    dotted name (or call target) ends with any of `names`, else None."""
    wanted = set(names)
    for dec in getattr(func_node, "decorator_list", []):
        target = dec.func if isinstance(dec, ast.Call) else dec
        dn = dotted_name(target)
        last = dn.split(".")[-1] if dn else ""
        if last in wanted or dn in wanted:
            return dec
    return None


def is_called_anywhere(tree, func_name):
    """True if `func_name` appears as a call target anywhere in the file.
    Used by 'wired at startup / registered' discriminators."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            dn = dotted_name(node.func)
            last = dn.split(".")[-1] if dn else ""
            if last == func_name or dn == func_name:
                return True
    return False


def line_of(node):
    return getattr(node, "lineno", "?")


def find_function(tree, func_name):
    """Return the first FunctionDef/AsyncFunctionDef named func_name, or None."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                and node.name == func_name:
            return node
    return None


def is_async(func_node):
    return isinstance(func_node, ast.AsyncFunctionDef)


BLOCKING_CALLS = {"sleep"}  # time.sleep etc. — expand as needed


def has_blocking_call(func_node):
    """True if the function body contains a blocking call like time.sleep(...)
    that is NOT awaited. Used to flag fake-async."""
    for node in ast.walk(func_node):
        if isinstance(node, ast.Call):
            dn = dotted_name(node.func)
            last = dn.split(".")[-1] if dn else ""
            if last in BLOCKING_CALLS:
                return True
    return False


def has_await(func_node):
    for node in ast.walk(func_node):
        if isinstance(node, ast.Await):
            return True
    return False


def returns_status_code(scope, code):
    """True if `scope` contains a literal `code` (e.g. 503) used plausibly as a
    status code: as an int literal argument or a status_code= keyword."""
    for node in ast.walk(scope):
        if isinstance(node, ast.Constant) and node.value == code:
            return True
    return False


def has_conditional(scope):
    """True if scope contains any If node."""
    return any(isinstance(n, ast.If) for n in ast.walk(scope))


def find_anchor_two_scope(func_nodes, trees, finder):
    """Two-scope anchor search over a MULTI-FILE claimed surface.

    `finder(scope)` returns a match (any truthy node) or None.
    Searches the claimed FUNCTIONS first (scope_label 'function'); if none match,
    searches each claimed FILE tree ('file'). Returns (match, scope_label).

    'function' => the claim is accurate (anchor in a named function).
    'file'     => MISLOCATED (anchor in a claimed file but not in a named function).
    None       => ABSENT (anchor nowhere in the claimed surface)."""
    for fn in func_nodes:
        m = finder(fn)
        if m is not None:
            return m, "function"
    for tree in trees:
        m = finder(tree)
        if m is not None:
            return m, "file"
    return None, None