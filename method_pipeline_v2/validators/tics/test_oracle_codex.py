"""
test_oracle_codex.py
────────────────────
Acceptance oracle for TICS, hand-derived from apps/codex BEFORE the graph
builder and scoring engine exist. Every expectation below was read off the
source by hand and is stated with the exact code that justifies it, so a
failure means the implementation disagrees with the repository — not that the
oracle drifted.

The four cases were chosen to cover the distinct paths through the scorer:

  1. cross-function via a direct CALL          (distance 1)
  2. cross-function via a common caller        (distance 3, needs real resolution)
  3. same function claimed by two NFRs         (distance 0)
  4. a SUPPORT pair                            (must be excluded from TICS)

Run:  pytest validators/tics/test_oracle_codex.py -v
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3] / "apps" / "codex"

# Decay used by the oracle: score = sqrt(S1*S2) * exp(-LAMBDA * (d - 1)) for d >= 1,
# and sqrt(S1*S2) for the same-function case. Kept here so a change to LAMBDA
# shows up as a deliberate oracle edit rather than a silent drift.
LAMBDA = 0.35
TOL = 0.02

pytestmark = pytest.mark.skipif(
    not REPO_ROOT.is_dir(), reason=f"codex sample not found at {REPO_ROOT}"
)


def decay(distance: int) -> float:
    return 1.0 if distance <= 0 else math.exp(-LAMBDA * (distance - 1))


# ─────────────────────────────────────────────────────────────────────────────
#  Case 1 — NFR 1.1 Limit Event Response  ↔  NFR 2.4 Transactions   (w = 0.75)
#
#  NOT a same-function case. `dispatch_pending_events` is claimed under 1.1 only;
#  `claim_batch` is claimed under 2.4. They are linked by a direct call:
#
#    app/workers/outbox.py:75   async with session.begin():          <- txn scope
#    app/workers/outbox.py:76       repository = OutboxRepository(session)
#    app/workers/outbox.py:77       events = await repository.claim_batch(...)
#    app/workers/outbox.py:79           async with self._limiter:    <- AsyncLimiter
#
#  Resolving line 77 needs local-variable type inference: `repository` takes its
#  type from the constructor call on line 76.
#
#  Architecturally this is a real tension and not an artefact: the rate limiter
#  throttles *inside* an open transaction, holding the transaction for the whole
#  admission delay.
# ─────────────────────────────────────────────────────────────────────────────
CASE_1 = {
    "pair": ("NFR 1.1", "NFR 2.4"),
    "f_a": "app/workers/outbox.py::OutboxDispatcher.dispatch_pending_events",
    "f_b": "app/repositories/outbox_repository.py::OutboxRepository.claim_batch",
    "edge": "CALLS",
    "distance": 1,
    "expected_c": 1.00,   # decay(1) == 1.0
}

# ─────────────────────────────────────────────────────────────────────────────
#  Case 2 — NFR 1.2 Multiple Copies  ↔  NFR 2.4 Transactions   (w = 1.00)
#
#  The heaviest pair, and invisible without a graph: neither claimed function
#  calls the other. They meet at a common caller.
#
#    EntityCache.set_json
#      ^-- CachedService._store_cached          (app/services/base_service.py)
#            ^-- OrderService.create            (app/services/order_service.py:99)
#                  |-- SqlAlchemyUnitOfWork.transaction   (order_service.py:32)
#
#  Undirected shortest path = 3. Requires all three of: inheritance resolution
#  (OrderService extends CachedService, so `self._store_cached` is inherited),
#  attribute typing from `CachedService.__init__(self, cache: EntityCache)`, and
#  local-variable typing for `unit_of_work = SqlAlchemyUnitOfWork(...)`.
# ─────────────────────────────────────────────────────────────────────────────
CASE_2 = {
    "pair": ("NFR 1.2", "NFR 2.4"),
    "f_a": "app/infrastructure/cache.py::EntityCache.set_json",
    "f_b": "app/infrastructure/unit_of_work.py::SqlAlchemyUnitOfWork.transaction",
    "edge": "CALLS",
    "distance": 3,
    "expected_c": 0.50,   # exp(-0.35 * 2) == 0.4966
}

# ─────────────────────────────────────────────────────────────────────────────
#  Case 3 — NFR 1.2 Multiple Copies  ↔  NFR 2.3 State Resync   (w = 0.50)
#
#  `EntityCache.set_json` is listed under BOTH NFR 1.2 and NFR 2.3 in
#  nfr-trace.json. Same function, distance 0, no decay.
# ─────────────────────────────────────────────────────────────────────────────
CASE_3 = {
    "pair": ("NFR 1.2", "NFR 2.3"),
    "f_a": "app/infrastructure/cache.py::EntityCache.set_json",
    "f_b": "app/infrastructure/cache.py::EntityCache.set_json",
    "edge": "SAME_FUNCTION",
    "distance": 0,
    "expected_c": 1.00,
}

# ─────────────────────────────────────────────────────────────────────────────
#  Case 4 — NFR 1.2 Multiple Copies  ↔  NFR 2.2 Graceful Degradation
#
#  Also shares get_json/set_json, so it would score ~1.0 on raw co-location.
#  But the pair is SUPPORT (w = 0.0): the cache is what *enables* degraded reads.
#  It must be excluded from the TICS denominator and reported under synergy.
#  Without this exclusion, an agent that correctly uses one mechanism to serve
#  two co-operating tactics is penalised for good design.
# ─────────────────────────────────────────────────────────────────────────────
CASE_4 = {
    "pair": ("NFR 1.2", "NFR 2.2"),
    "shared_function": "app/infrastructure/cache.py::EntityCache.get_json",
    "weight": 0.0,
    "must_be_excluded_from_tics": True,
}


# ─────────────────────────────────────────────────────────────────────────────
#  Ground-truth tests that need no implementation — these run today.
# ─────────────────────────────────────────────────────────────────────────────
def test_conf_tacticset_covers_all_fifteen_pairs():
    """Six NFRs give C(6,2) = 15 ordered-insensitive pairs; none may be missing."""
    import json

    data = json.loads((Path(__file__).parent / "data" / "conf_tacticset.json").read_text())
    pairs = {frozenset((p["a"], p["b"])) for p in data["pairs"]}
    assert len(data["pairs"]) == 15, "duplicate or missing pair entries"
    assert len(pairs) == 15, "the same pair is listed twice"

    nfrs = list(data["nfrs"])
    expected = {frozenset((a, b)) for i, a in enumerate(nfrs) for b in nfrs[i + 1:]}
    assert pairs == expected


def test_tics_denominator_is_documented():
    """The denominator is every pair with weight > 0. Guard it: an accidental
    edit to a weight silently rescales every reported TICS number."""
    import json

    data = json.loads((Path(__file__).parent / "data" / "conf_tacticset.json").read_text())
    scoring = [p for p in data["pairs"] if p["weight"] > 0]
    support = [p for p in data["pairs"] if p["weight"] == 0]

    assert len(scoring) + len(support) == 15
    # 13 with NFR 2.1 x 2.2 read as Low (prose), 12 if read as Support (matrix).
    assert len(scoring) in (12, 13), f"unexpected denominator {len(scoring)}"


def test_trace_functions_referenced_by_oracle_exist_in_trace():
    """Every function this oracle asserts on must actually be claimed in the
    sample's nfr-trace.json, or the oracle is testing something imaginary."""
    import json

    from validators.tics.contract import normalize_function_ref, normalize_nfr_id

    trace = json.loads((REPO_ROOT / "nfr-trace.json").read_text(encoding="utf-8-sig"))
    claimed: set[tuple[str, str]] = set()
    for entry in trace["nfrTrace"]:
        nfr_id = normalize_nfr_id(entry["nfr"])
        for ref in entry["functionNames"]:
            claimed.add((nfr_id, normalize_function_ref(ref)))

    for case in (CASE_1, CASE_2, CASE_3):
        nfr_a, nfr_b = case["pair"]
        assert (nfr_a, case["f_a"]) in claimed, f"{case['f_a']} not claimed under {nfr_a}"
        assert (nfr_b, case["f_b"]) in claimed, f"{case['f_b']} not claimed under {nfr_b}"

    nfr_a, nfr_b = CASE_4["pair"]
    assert (nfr_a, CASE_4["shared_function"]) in claimed
    assert (nfr_b, CASE_4["shared_function"]) in claimed


# ─────────────────────────────────────────────────────────────────────────────
#  Implementation tests — skipped until Phase 1/2/4 land.
# ─────────────────────────────────────────────────────────────────────────────
def _phase1_missing() -> bool:
    return importlib.util.find_spec("validators.tics.extractors.python_extractor") is None


# Scoped to the implementation tests only. A module-level importorskip would
# also skip the ground-truth tests above, which must run from day one.
needs_phase1 = pytest.mark.skipif(
    _phase1_missing(), reason="Phase 1 (CodeGraphBuilder) not implemented yet"
)


@needs_phase1
@pytest.mark.parametrize("case", [CASE_1, CASE_2, CASE_3], ids=lambda c: "-".join(c["pair"]))
def test_shortest_path_matches_oracle(case):
    from validators.tics.extractors.python_extractor import PythonExtractor

    graph = PythonExtractor().build_graph(REPO_ROOT, source_roots=["app"])
    assert graph.distance(case["f_a"], case["f_b"]) == case["distance"]


@needs_phase1
@pytest.mark.parametrize("case", [CASE_1, CASE_2, CASE_3], ids=lambda c: "-".join(c["pair"]))
def test_pair_score_matches_oracle(case):
    """With S pinned to 1.0 the pair score is exactly its distance decay, which
    isolates the graph from the confidence model while the latter is still open."""
    from validators.tics.contract import TraceOnlyBindingProvider
    from validators.tics.extractors.python_extractor import PythonExtractor
    from validators.tics.scoring import pair_score

    graph = PythonExtractor().build_graph(REPO_ROOT, source_roots=["app"])
    bindings = TraceOnlyBindingProvider().bindings(REPO_ROOT)

    got = pair_score(graph, bindings, *case["pair"])
    assert got.value == pytest.approx(case["expected_c"], abs=TOL)
    assert got.distance == case["distance"]


@needs_phase1
def test_support_pair_excluded_from_tics():
    from validators.tics.contract import TraceOnlyBindingProvider
    from validators.tics.extractors.python_extractor import PythonExtractor
    from validators.tics.scoring import score_repository

    graph = PythonExtractor().build_graph(REPO_ROOT, source_roots=["app"])
    result = score_repository(graph, TraceOnlyBindingProvider().bindings(REPO_ROOT))

    pair = frozenset(CASE_4["pair"])
    assert pair not in {frozenset(p.pair) for p in result.scoring_pairs}
    assert pair in {frozenset(p.pair) for p in result.synergy_pairs}, (
        "support pairs must still be measured and reported, just not scored"
    )
