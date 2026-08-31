"""
contract.py
───────────
The boundary between TICS and the component that scores S(x,f) — the confidence
that function `f` really implements tactic `x`. That component is owned by
someone else and its formula is still being settled, so TICS depends on this
interface and never on their concrete class.

Why an interface rather than a direct call:

  • TICS SHOULD track their formula. When they change how S is computed, TICS
    consumes the new numbers on the next run with no edit here. That is the
    whole point of calling in-process instead of exchanging stale files.

  • TICS SHOULD NOT track their internals. Method names, constructor shape and
    module layout are theirs to change. Those changes break one thin adapter
    on their side, not the scoring engine or its tests.

The JSON dump is a by-product, not the transport. Archiving the exact bindings
that produced a reported TICS number is what makes a run re-derivable months
later, and it lets TICS run standalone against an archived repository.
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0"

# "NFR 1.1 Limit Event Response" -> "NFR 1.1". Both sides must agree on the join
# key, and the free-text remainder is not it: agents have been observed writing
# their own tactic taxonomies into the trace.
_NFR_ID = re.compile(r"^\s*NFR\s*([0-9]+\.[0-9]+)")


def normalize_nfr_id(raw: str) -> str | None:
    """Reduce a trace's `nfr` field to its stable id, or None if unparseable."""
    match = _NFR_ID.match(raw)
    return f"NFR {match.group(1)}" if match else None


def normalize_function_ref(raw: str) -> str:
    """Canonical form of a function reference: `relative/path.py::Qualified.name`.

    Both sides must produce byte-identical refs or the join silently yields
    nothing, so the normalisation lives here rather than in either component.
    """
    ref = raw.strip().replace("\\", "/")
    path, sep, func = ref.partition("::")
    return f"{path.lstrip('./')}{sep}{func.strip()}" if sep else ref.lstrip("./")


def read_trace_labels(repo_root: Path, trace_filename: str = "nfr-trace.json") -> dict[str, str]:
    """`{"NFR 1.1": "Limit Event Response", ...}` straight from a trace file.

    The label is what `normalize_nfr_id` throws away, and it is the only thing
    that distinguishes one generation of the prompt from another.
    """
    trace = json.loads((repo_root / trace_filename).read_text(encoding="utf-8-sig"))
    labels: dict[str, str] = {}
    for entry in trace.get("nfrTrace", []):
        raw = entry.get("nfr", "")
        nfr_id = normalize_nfr_id(raw)
        if nfr_id:
            labels[nfr_id] = raw[len(nfr_id):].lstrip(" :.-").strip() or raw
    return labels


def _tokens(text: str) -> set[str]:
    return {t for t in re.split(r"[^a-z0-9]+", text.lower()) if t and t != "of"}


def nfr_set_mismatches(labels: dict[str, str], expected: dict[str, str]) -> list[str]:
    """Which NFR ids name a different requirement than the ground truth expects.

    Matching on the id alone is not safe. Earlier prompt generations reused the
    same numbering for entirely different requirements — "NFR 1.2" was
    "Concurrency & Resource Utilization" before it was "Maintain Multiple Copies
    of Data" — so a repository from an older generation would silently score
    against tactics it was never asked to implement, and produce a plausible
    number that means nothing. Comparing the label catches that.
    """
    problems: list[str] = []
    for nfr_id, expected_name in expected.items():
        actual = labels.get(nfr_id)
        if actual is None:
            problems.append(f"{nfr_id}: absent from trace")
            continue
        wanted, got = _tokens(expected_name), _tokens(actual)
        if not wanted or len(wanted & got) / len(wanted) < 0.6:
            problems.append(f"{nfr_id}: trace says {actual!r}, ground truth expects {expected_name!r}")
    return problems


@dataclass(frozen=True)
class TacticBinding:
    """One validated (tactic, function) claim with its implementation confidence.

    Only claims that survived static verification belong here. A fabricated or
    missing function must arrive with s=0.0 rather than be dropped, so TICS can
    report honest coverage instead of silently shrinking its own denominator.
    """

    nfr_id: str                 # stable id, e.g. "NFR 1.1"
    function_ref: str           # "app/workers/outbox.py::OutboxDispatcher.dispatch_pending_events"
    s: float                    # implementation confidence in [0, 1]
    evidence: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.s <= 1.0:
            raise ValueError(f"S must lie in [0, 1], got {self.s} for {self.function_ref}")


class ITacticBindingProvider(ABC):
    """Supplies validated tactic→function bindings for one generated repository."""

    @abstractmethod
    def bindings(self, repo_root: Path) -> list[TacticBinding]:
        ...


class TraceOnlyBindingProvider(ITacticBindingProvider):
    """Degraded provider: every function named in the trace scores S=1.0.

    Lets the graph builder and the scoring engine be developed and tested before
    the real provider exists. Results are NOT publishable — with S pinned to 1.0
    every pair score collapses to its distance decay, so a fabricated function
    counts exactly as much as a verified one. `degraded=True` rides along in the
    evidence dict so a report built on this provider is self-identifying.
    """

    def __init__(self, trace_filename: str = "nfr-trace.json") -> None:
        self._trace_filename = trace_filename

    def bindings(self, repo_root: Path) -> list[TacticBinding]:
        trace = json.loads((repo_root / self._trace_filename).read_text(encoding="utf-8-sig"))
        out: list[TacticBinding] = []
        for entry in trace.get("nfrTrace", []):
            nfr_id = normalize_nfr_id(entry.get("nfr", ""))
            if nfr_id is None:
                continue
            for ref in entry.get("functionNames", []):
                out.append(
                    TacticBinding(
                        nfr_id=nfr_id,
                        function_ref=normalize_function_ref(ref),
                        s=1.0,
                        evidence={"degraded": True},
                    )
                )
        return out


def dump_bindings(bindings: list[TacticBinding], path: Path, repo_root: Path) -> Path:
    """Archive the bindings a run scored against, for reproducibility."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schemaVersion": SCHEMA_VERSION,
        "repoRoot": str(repo_root),
        "bindings": [asdict(b) for b in bindings],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def load_bindings(path: Path) -> list[TacticBinding]:
    """Read back an archived dump; the inverse of `dump_bindings`."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schemaVersion") != SCHEMA_VERSION:
        raise ValueError(
            f"bindings schemaVersion {payload.get('schemaVersion')!r} "
            f"!= expected {SCHEMA_VERSION!r}"
        )
    return [
        TacticBinding(
            nfr_id=b["nfrId"] if "nfrId" in b else b["nfr_id"],
            function_ref=normalize_function_ref(
                b["functionRef"] if "functionRef" in b else b["function_ref"]
            ),
            s=float(b["s"]),
            evidence=b.get("evidence", {}),
        )
        for b in payload["bindings"]
    ]
