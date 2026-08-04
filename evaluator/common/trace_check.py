"""Resolving traceability claims against delivered source.

Both profiles ask the agent to name, in a machine-readable file, the files and
functions that implement each tactic. This module answers one narrow question
about those claims: does the named thing exist, verbatim, where it was said to
be?

That is deliberately less than it sounds. A function can exist, carry a
plausible name, and do nothing at all. Nothing here establishes that a tactic
works -- only that the claim is resolvable. Treating a resolved reference as
evidence of a working mechanism is the mistake this docstring exists to
prevent.

Two things are checked beyond existence, because both are cheap and both catch
claims that are resolvable but still false:

  * whether the cited function's own body mentions the library it is claimed to
    use, which catches an entry pointing at the outer request handler rather
    than the function that actually calls into the mechanism;
  * whether a cited symbol is a function at all, rather than a module or a
    variable that happens to share the name.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Reference:
    """A 'relative/path.py::qualified.name' claim, split into its parts."""

    raw: str
    rel_path: str
    qualified: str

    @classmethod
    def parse(cls, reference: str) -> "Reference | None":
        if "::" not in reference:
            return None
        rel, _, qualified = reference.partition("::")
        rel, qualified = rel.strip(), qualified.strip()
        if not rel or not qualified:
            return None
        return cls(reference, rel, qualified)


def function_exists(app_dir: Path, reference: str) -> bool:
    """Whether a 'path.py::name' reference resolves to a real function.

    Parsed rather than imported: importing would execute module-level code from
    an application we are evaluating, and would fail for anything that expects a
    live database at import time. Nested names are matched on their qualified
    path, so Class.method resolves only inside that class.
    """
    return _find_node(app_dir, reference) is not None


def function_mentions(app_dir: Path, reference: str, needles: list[str]) -> bool:
    """Whether any needle appears within the cited function's own source.

    Used to corroborate a `librariesUsed` claim against the function said to
    call into it. Substring matching over the function's segment of the file --
    imprecise by design, since a decorator, an attribute call and an aliased
    import are all legitimate ways to reach a library, and enumerating them
    would reject correct code. A negative result is therefore a signal to look,
    not a verdict.
    """
    node = _find_node(app_dir, reference)
    if node is None:
        return False

    parsed = Reference.parse(reference)
    if parsed is None:
        return False
    source = _read(app_dir / parsed.rel_path)
    if not source:
        return False

    try:
        segment = ast.get_source_segment(source, node) or ""
    except (ValueError, TypeError):
        return False

    # Decorators sit above the node's own segment on some Python versions, so
    # include them explicitly rather than depending on that detail.
    for decorator in getattr(node, "decorator_list", []):
        segment += "\n" + (ast.get_source_segment(source, decorator) or "")

    lowered = segment.lower()
    return any(n.lower() in lowered for n in needles if n)


def _find_node(app_dir: Path, reference: str) -> ast.AST | None:
    parsed = Reference.parse(reference)
    if parsed is None:
        return None

    source_path = app_dir / parsed.rel_path
    if not source_path.is_file():
        return None

    source = _read(source_path)
    if not source:
        return None

    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return None

    return _qualified_nodes(tree).get(parsed.qualified)


def _qualified_nodes(tree: ast.AST) -> dict[str, ast.AST]:
    """Map every function/class name to its node, both qualified and bare.

    The bare name is accepted too, because a method is unambiguous when no
    same-named sibling exists elsewhere in the file; requiring full
    qualification would reject honest entries for a stylistic reason. Where a
    bare name is ambiguous the first definition wins, which is why the
    qualified form is the one worth asking agents for.
    """
    found: dict[str, ast.AST] = {}

    def walk(node: ast.AST, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                qualified = f"{prefix}.{child.name}" if prefix else child.name
                found.setdefault(qualified, child)
                found.setdefault(child.name, child)
                walk(child, qualified)
            else:
                walk(child, prefix)

    walk(tree, "")
    return found


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""
