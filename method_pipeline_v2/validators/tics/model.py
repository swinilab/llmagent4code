"""
model.py
────────
Language-neutral code graph. Nothing in this module knows about Python: it is
plain data plus a traversal, so the scoring engine and every future language
frontend share one representation.

Distance is measured on the UNDIRECTED graph. Two tactics rarely call each
other — they meet at a common caller, which is exactly the shape the source
document describes (`update_order` calling both `cache.invalidate` and
`transaction.commit`, counted as distance 2). Following call direction only
would score that pair as unreachable.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Iterable, Iterator

# Edge kinds. Only CALLS is built. TXN_BOUNDARY and the co-participation kinds
# were prototyped and set aside: a transaction scope can sit in the calling
# function, in a unit-of-work object, or several frames up, and deciding which
# counts is a design question in its own right. The constants stay so an older
# graph dump still loads, and so the intent is on the record.
CALLS = "CALLS"
REGISTERED = "REGISTERED"
SHARED_STATE = "SHARED_STATE"
USES_CONFIG = "USES_CONFIG"
USES_RESOURCE = "USES_RESOURCE"
TXN_BOUNDARY = "TXN_BOUNDARY"



@dataclass(frozen=True)
class FunctionNode:
    """One function or method, addressed the same way nfr-trace.json addresses it."""

    ref: str                    # "app/workers/outbox.py::OutboxDispatcher.claim_batch"
    file: str                   # "app/workers/outbox.py"
    qualname: str               # "OutboxDispatcher.claim_batch"
    lineno: int = 0
    class_name: str | None = None


@dataclass(frozen=True)
class Edge:
    src: str
    dst: str
    kind: str
    detail: str = ""            # why this edge exists, e.g. the call expression


@dataclass
class Path:
    """A shortest connection between two functions, kept for the report so a
    reviewer can audit why a pair scored what it scored."""

    distance: int
    refs: list[str] = field(default_factory=list)
    kinds: list[str] = field(default_factory=list)


class CodeGraph:
    def __init__(self) -> None:
        self._nodes: dict[str, FunctionNode] = {}
        self._edges: list[Edge] = []
        self._adjacency: dict[str, dict[str, str]] = {}   # ref -> neighbour -> kind
        # Diagnostics. `external` (a call into stdlib or a third-party package) is
        # expected and harmless — those targets are outside the graph by design.
        # `unresolved` is the number that matters: first-party calls the frontend
        # could not type. Reporting them together would hide the second behind
        # the first, since library calls dominate any real codebase.
        self.external_calls: int = 0
        self.nodeless_calls: int = 0
        self.unresolved_calls: int = 0
        # A count alone cannot be audited: a missed edge changes a distance, and
        # a distance changes a score. These samples name the call expression and
        # where it sits, so a reviewer can judge whether the misses matter or are
        # all in code no conflicting tactic touches. Bounded — the count above
        # stays exact regardless.
        self.unresolved_samples: list[dict] = []
        # Functions a framework invokes through a decorator (@router.post,
        # @app.exception_handler). There is no first-party node to draw an edge
        # from, so integration is recorded as a property of the node instead.
        self.framework_entrypoints: set[str] = set()

    # ── construction ────────────────────────────────────────────────────────
    def add_node(self, node: FunctionNode) -> None:
        self._nodes.setdefault(node.ref, node)
        self._adjacency.setdefault(node.ref, {})

    def add_edge(self, src: str, dst: str, kind: str = CALLS, detail: str = "") -> None:
        """Record an edge. Self-loops are dropped: a function reaching itself is
        distance 0 by definition and a loop would only pad the adjacency."""
        if src == dst or src not in self._nodes or dst not in self._nodes:
            return
        self._edges.append(Edge(src, dst, kind, detail))
        self._adjacency[src].setdefault(dst, kind)
        self._adjacency[dst].setdefault(src, kind)

    # ── inspection ──────────────────────────────────────────────────────────
    def __contains__(self, ref: str) -> bool:
        return ref in self._nodes

    def __len__(self) -> int:
        return len(self._nodes)

    @property
    def nodes(self) -> Iterator[FunctionNode]:
        return iter(self._nodes.values())

    @property
    def edges(self) -> list[Edge]:
        return list(self._edges)

    def node(self, ref: str) -> FunctionNode | None:
        return self._nodes.get(ref)

    def neighbours(self, ref: str) -> Iterable[str]:
        return self._adjacency.get(ref, {}).keys()

    def edges_of_kind(self, kind: str) -> list[Edge]:
        return [e for e in self._edges if e.kind == kind]

    # ── traversal ───────────────────────────────────────────────────────────
    def distance(self, a: str, b: str, max_distance: int = 6) -> int | None:
        """Undirected hop count, 0 when a is b, None when unreachable or beyond
        `max_distance`. The cap matters: without it, a small repository becomes
        fully connected through common utilities and every pair scores nonzero."""
        path = self.shortest_path(a, b, max_distance)
        return path.distance if path is not None else None

    def shortest_path(self, a: str, b: str, max_distance: int = 6) -> Path | None:
        """Breadth-first: every call is one hop, so the first time we reach `b`
        is by a shortest path."""
        if a not in self._nodes or b not in self._nodes:
            return None
        if a == b:
            return Path(distance=0, refs=[a], kinds=[])

        previous: dict[str, str] = {a: ""}
        queue: deque[tuple[str, int]] = deque([(a, 0)])
        while queue:
            current, depth = queue.popleft()
            if depth >= max_distance:
                continue
            for neighbour in self._adjacency.get(current, ()):
                if neighbour in previous:
                    continue
                previous[neighbour] = current
                if neighbour == b:
                    return self._rebuild(previous, a, b)
                queue.append((neighbour, depth + 1))
        return None

    def _rebuild(self, previous: dict[str, str], a: str, b: str) -> Path:
        refs = [b]
        while refs[-1] != a:
            refs.append(previous[refs[-1]])
        refs.reverse()
        kinds = [self._adjacency[refs[i]][refs[i + 1]] for i in range(len(refs) - 1)]
        return Path(distance=len(refs) - 1, refs=refs, kinds=kinds)

    # ── serialisation ───────────────────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "nodes": [
                {
                    "ref": n.ref,
                    "file": n.file,
                    "qualname": n.qualname,
                    "lineno": n.lineno,
                    "className": n.class_name,
                }
                for n in self._nodes.values()
            ],
            "edges": [
                {"src": e.src, "dst": e.dst, "kind": e.kind, "detail": e.detail}
                for e in self._edges
            ],
            "diagnostics": {
                "externalCalls": self.external_calls,
                "nodelessCalls": self.nodeless_calls,
                "unresolvedCalls": self.unresolved_calls,
                "unresolvedSamples": self.unresolved_samples,
                "frameworkEntrypoints": sorted(self.framework_entrypoints),
            },
        }

    @classmethod
    def from_dict(cls, payload: dict) -> CodeGraph:
        graph = cls()
        for n in payload["nodes"]:
            graph.add_node(
                FunctionNode(
                    ref=n["ref"],
                    file=n["file"],
                    qualname=n["qualname"],
                    lineno=n.get("lineno", 0),
                    class_name=n.get("className"),
                )
            )
        for e in payload["edges"]:
            graph.add_edge(e["src"], e["dst"], e["kind"], e.get("detail", ""))
        diagnostics = payload.get("diagnostics", {})
        graph.external_calls = diagnostics.get("externalCalls", 0)
        graph.nodeless_calls = diagnostics.get("nodelessCalls", 0)
        graph.unresolved_calls = diagnostics.get("unresolvedCalls", 0)
        graph.unresolved_samples = diagnostics.get("unresolvedSamples", [])
        graph.framework_entrypoints = set(diagnostics.get("frameworkEntrypoints", []))
        return graph
