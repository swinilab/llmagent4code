"""
scoring.py
──────────
Tactic Interaction Conflict Score. Pure functions over a CodeGraph and a list of
TacticBindings — no AST, no file system beyond loading the ground truth, so this
module is identical for every language frontend.

Three modelling choices, each answering a specific failure of the naive formula:

  geometric mean over the two confidences
      A pair is only as strong as its weaker half. An arithmetic mean lets a
      solidly-implemented tactic carry a barely-present one to a high score.

  exponential distance decay, not 1/d
      1/d drops to 20% at distance 5, which is too harsh for repository-scale
      graphs where a four-hop architectural interaction is still real.

  max over function pairs, aggregated per tactic pair before the system score
      Tactics have unequal function counts. Averaging every (f1, f2) combination
      lets 29 weak paths bury one strong one: 1x0.95 + 29x0.05 averages to 0.08
      and the finding disappears.

What this measures is EXPOSURE, not impact. A high score says two conflicting
tactics were implemented on interacting code paths — it does not say latency
rose or consistency broke, and it is not "worse architecture". Invalidating a
cache immediately after a commit scores high and is correct design. Whether the
agent recognised and resolved the tension is a question for the ADR and runtime
evidence, not for this number.
"""

from __future__ import annotations

import json
import math
import random
import statistics
from dataclasses import dataclass, field
from pathlib import Path

from validators.tics.contract import TacticBinding
from validators.tics.model import CodeGraph

DEFAULT_LAMBDA = 0.35
DEFAULT_MAX_DISTANCE = 6
_DATA = Path(__file__).parent / "data" / "conf_tacticset.json"


def decay(distance: int, lambda_: float = DEFAULT_LAMBDA) -> float:
    """1.0 for the same function or a direct link, tapering with each extra hop."""
    return 1.0 if distance <= 0 else math.exp(-lambda_ * (distance - 1))


# ─────────────────────────────────────────────────────────────────────────────
#  Ground truth
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class ConfTacticSet:
    weights: dict[frozenset[str], float]
    rationales: dict[frozenset[str], str]
    nfr_names: dict[str, str]

    def weight(self, a: str, b: str) -> float:
        return self.weights.get(frozenset((a, b)), 0.0)

    @property
    def scoring_pairs(self) -> list[tuple[str, str]]:
        """Pairs that count toward TICS — everything with a non-zero weight."""
        return [tuple(sorted(p)) for p, w in self.weights.items() if w > 0]

    @property
    def support_pairs(self) -> list[tuple[str, str]]:
        """Synergistic pairs. Measured and reported, never scored: penalising an
        agent for serving two co-operating tactics from one mechanism would
        punish exactly the design we want to see."""
        return [tuple(sorted(p)) for p, w in self.weights.items() if w == 0]


def load_conf_tacticset(path: Path | None = None) -> ConfTacticSet:
    payload = json.loads(Path(path or _DATA).read_text(encoding="utf-8"))
    weights: dict[frozenset[str], float] = {}
    rationales: dict[frozenset[str], str] = {}
    for pair in payload["pairs"]:
        key = frozenset((pair["a"], pair["b"]))
        weights[key] = float(pair["weight"])
        rationales[key] = pair.get("rationale", "")
    return ConfTacticSet(weights, rationales, payload.get("nfrs", {}))


# ─────────────────────────────────────────────────────────────────────────────
#  Scoring
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class PairScore:
    pair: tuple[str, str]
    value: float
    weight: float
    distance: int | None = None
    f_a: str | None = None
    f_b: str | None = None
    path: list[str] = field(default_factory=list)
    kinds: list[str] = field(default_factory=list)

    @property
    def found(self) -> bool:
        return self.distance is not None


@dataclass(frozen=True)
class Baseline:
    """Ambient connectivity of the graph, measured on random function pairs.

    Without this, TICS is uninterpretable and indefensible: "conflicting tactics
    are 2 hops apart" means nothing until you know whether *everything* in this
    repository is 2 hops apart. It also makes the score comparable across agents,
    whose generated codebases differ in size and layering depth.
    """

    median_distance: float
    mean_distance: float
    reachable_fraction: float
    sample_size: int


@dataclass(frozen=True)
class RepositoryScore:
    tics: float
    coverage: float                       # scoring pairs with any interaction found
    scoring_pairs: list[PairScore]
    synergy_pairs: list[PairScore]
    implementation: dict[str, float] = field(default_factory=dict)
    # Share of the fixed 13-pair ground truth that actually entered the TICS
    # calculation. Low means the score rests on a small part of the template and
    # should be read with that in mind.
    applicable_mass: float = 0.0
    baseline: Baseline | None = None
    unclaimed_nfrs: list[str] = field(default_factory=list)

    @property
    def conformance(self) -> float:
        """Mean implementation across the fixed tactic set. High is good.

        Deliberately NOT combined with tics: one says how much was built, the
        other how entangled what was built is, and a single number would let a
        thin implementation pass as a clean architecture.
        """
        return (
            sum(self.implementation.values()) / len(self.implementation)
            if self.implementation else 0.0
        )

    # ── diagnostics kept from the unconditioned formula ─────────────────────
    #
    # TICS used to be the plain weighted mean over all thirteen pairs, which
    # factors exactly into `breadth * intensity`. On the first five-repository
    # sample breadth ranged 0.11-1.00 while intensity stayed inside 0.60-0.90, so
    # that number tracked breadth (r = +0.96) and barely tracked intensity
    # (r = +0.14) — it mostly re-reported NFR coverage under another name, and
    # rewarded building less. Conditioning on implementation replaced it. These
    # two stay as diagnostics: they explain where a TICS value comes from, and
    # breadth is still the honest answer to "how much of the ground truth had any
    # interaction at all".
    @property
    def breadth(self) -> float:
        """Weighted fraction of conflicting pairs with any interaction found."""
        total = sum(p.weight for p in self.scoring_pairs)
        found = sum(p.weight for p in self.scoring_pairs if p.found)
        return found / total if total else 0.0

    @property
    def intensity(self) -> float:
        """Weighted mean pair score over the pairs that were found."""
        found = [p for p in self.scoring_pairs if p.found]
        weight = sum(p.weight for p in found)
        return sum(p.weight * p.value for p in found) / weight if weight else 0.0

    @property
    def median_conflict_distance(self) -> float | None:
        found = [p.distance for p in self.scoring_pairs if p.found]
        return statistics.median(found) if found else None

    @property
    def proximity_lift(self) -> float | None:
        """How much closer conflicting tactics sit than an arbitrary pair.

        Above 1.0 means the agent concentrated conflicting tactics on shared
        paths beyond what the codebase's own layering would produce by chance.
        """
        if self.baseline is None or self.median_conflict_distance is None:
            return None
        observed = max(self.median_conflict_distance, 0.5)   # same-function -> 0
        return self.baseline.median_distance / observed

    @property
    def mean_pair(self) -> float:
        found = [p.value for p in self.scoring_pairs if p.found]
        return sum(found) / len(found) if found else 0.0

    @property
    def max_pair(self) -> float:
        return max((p.value for p in self.scoring_pairs), default=0.0)


def measure_baseline(
    graph: CodeGraph,
    *,
    sample_size: int = 4000,
    max_distance: int = DEFAULT_MAX_DISTANCE,
    seed: int = 0,
) -> Baseline:
    """Sample random function pairs to characterise the graph's own density.

    Seeded so a reported baseline is reproducible; sampled rather than exhaustive
    because all-pairs BFS is quadratic and the estimate converges quickly.
    """
    refs = [node.ref for node in graph.nodes]
    if len(refs) < 2:
        return Baseline(0.0, 0.0, 0.0, 0)

    rng = random.Random(seed)
    distances: list[int] = []
    attempts = 0
    for _ in range(sample_size):
        a, b = rng.choice(refs), rng.choice(refs)
        if a == b:
            continue
        attempts += 1
        distance = graph.distance(a, b, max_distance)
        if distance is not None:
            distances.append(distance)

    if not distances:
        return Baseline(0.0, 0.0, 0.0, attempts)
    return Baseline(
        median_distance=statistics.median(distances),
        mean_distance=statistics.mean(distances),
        reachable_fraction=len(distances) / attempts if attempts else 0.0,
        sample_size=attempts,
    )


def _by_nfr(bindings: list[TacticBinding]) -> dict[str, list[TacticBinding]]:
    grouped: dict[str, list[TacticBinding]] = {}
    for binding in bindings:
        grouped.setdefault(binding.nfr_id, []).append(binding)
    return grouped


def pair_score(
    graph: CodeGraph,
    bindings: list[TacticBinding],
    nfr_a: str,
    nfr_b: str,
    *,
    weight: float = 1.0,
    lambda_: float = DEFAULT_LAMBDA,
    max_distance: int = DEFAULT_MAX_DISTANCE,
) -> PairScore:
    """Strongest interaction between any function pair implementing the two tactics."""
    grouped = _by_nfr(bindings)
    candidates: list[PairScore] = []

    for a in grouped.get(nfr_a, []):
        for b in grouped.get(nfr_b, []):
            if a.s <= 0.0 or b.s <= 0.0:
                continue          # an unverified claim carries no evidence
            path = graph.shortest_path(a.function_ref, b.function_ref, max_distance)
            if path is None:
                continue
            candidates.append(
                PairScore(
                    pair=(nfr_a, nfr_b),
                    value=math.sqrt(a.s * b.s) * decay(path.distance, lambda_),
                    weight=weight,
                    distance=path.distance,
                    f_a=a.function_ref,
                    f_b=b.function_ref,
                    path=path.refs,
                    kinds=path.kinds,
                )
            )

    if not candidates:
        return PairScore(pair=(nfr_a, nfr_b), value=0.0, weight=weight)

    # Ties are common and must not be broken by iteration order: decay(0) and
    # decay(1) are both 1.0, so a same-function pair and a direct call score
    # identically. Prefer the shorter distance — one function implementing both
    # tactics is stronger structural evidence than two functions one hop apart —
    # then order by ref so the reported witness is reproducible across runs.
    candidates.sort(key=lambda c: (-c.value, c.distance, c.f_a, c.f_b))
    return candidates[0]


# A claimed function that nothing else touches does not implement a tactic in the
# system, whatever the trace says. Degree 2 is the lowest bar that means "takes
# part in more than one relationship".
MIN_WIRED_DEGREE = 2


def implementation_by_nfr(
    graph: CodeGraph, bindings: list[TacticBinding]
) -> dict[str, float]:
    """How substantively each tactic is present, in [0, 1].

    Two signals, multiplied per function and averaged per tactic:

        S(x, f)        is this function really an implementation of the tactic
        wired(f)       is it connected to anything else in the repository

    Both are needed. S alone cannot see that a genuine rate limiter is called
    from exactly one place; wiring alone cannot see that `OMSException.__init__`
    is not exception detection. While S is pinned at 1.0 this reduces to the
    wiring test, which is why a degraded run must not be read as a verdict.

    This exists because the tactic set is fixed and every sampled repository
    claimed all six NFRs: absence never shows up as a missing binding, only as a
    claim with nothing attached to it.
    """
    per_nfr: dict[str, list[float]] = {}
    for binding in bindings:
        if binding.function_ref not in graph:
            per_nfr.setdefault(binding.nfr_id, []).append(0.0)
            continue
        wired = (
            len(list(graph.neighbours(binding.function_ref))) >= MIN_WIRED_DEGREE
            # A framework entry point has no first-party caller by construction —
            # a decorated route, a registered middleware — yet the framework runs
            # it on every request. Counting it as unwired would penalise exactly
            # the idiomatic way to integrate a tactic in a web framework.
            or binding.function_ref in graph.framework_entrypoints
        )
        per_nfr.setdefault(binding.nfr_id, []).append(binding.s if wired else 0.0)
    return {nfr: sum(v) / len(v) for nfr, v in per_nfr.items() if v}


def score_repository(
    graph: CodeGraph,
    bindings: list[TacticBinding],
    conf: ConfTacticSet | None = None,
    *,
    lambda_: float = DEFAULT_LAMBDA,
    max_distance: int = DEFAULT_MAX_DISTANCE,
    with_baseline: bool = True,
) -> RepositoryScore:
    conf = conf or load_conf_tacticset()
    grouped = _by_nfr(bindings)

    def score(pairs: list[tuple[str, str]]) -> list[PairScore]:
        return [
            pair_score(
                graph, bindings, a, b,
                weight=conf.weight(a, b), lambda_=lambda_, max_distance=max_distance,
            )
            for a, b in sorted(pairs)
        ]

    scoring = score(conf.scoring_pairs)
    synergy = score(conf.support_pairs)

    # TICS is conditioned on implementation. A pair leaves the calculation when
    # either tactic is absent, rather than counting as "no conflict found":
    # otherwise the way to score well is to build less, which inverts what the
    # metric is for. Conformance is reported beside it and never folded in, so an
    # agent that skipped half the tactic set looks bad there instead of flattered
    # here.
    implementation = implementation_by_nfr(graph, bindings)
    applicable = [
        (p, p.weight * implementation.get(p.pair[0], 0.0) * implementation.get(p.pair[1], 0.0))
        for p in scoring
    ]
    mass = sum(m for _, m in applicable)
    tics = sum(m * p.value for p, m in applicable) / mass if mass else 0.0
    found = sum(1 for p in scoring if p.found)

    return RepositoryScore(
        tics=tics,
        coverage=found / len(scoring) if scoring else 0.0,
        implementation=implementation,
        applicable_mass=mass / sum(p.weight for p in scoring) if scoring else 0.0,
        scoring_pairs=scoring,
        synergy_pairs=synergy,
        baseline=measure_baseline(graph, max_distance=max_distance) if with_baseline else None,
        # An NFR with no binding cannot participate in any pair. Reporting it
        # stops a trace that simply omits a tactic from reading as "no conflict".
        unclaimed_nfrs=[n for n in conf.nfr_names if n not in grouped],
    )
