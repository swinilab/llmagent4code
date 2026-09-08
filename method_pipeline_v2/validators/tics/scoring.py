"""
scoring.py
──────────
Tactic Interaction Conflict Score. Pure functions over a CodeGraph and a list of
TacticBindings — no AST, no file system beyond loading the ground truth, so this
module is identical for every language frontend.

The whole measure is four lines, and the paper's "Static Architectural
Measurement" section is its specification:

    conf_func(t, f)           = stage 3's score_func(t, f)          in {0, 0.5, 1}
    conf_pair(t1,t2, f1,f2)   = sqrt(conf_func(t1,f1) * conf_func(t2,f2)) / (1 + d)
    conf_tactic(t1, t2)       = max over every (f1, f2)
    TICS = conf(tacticset)    = sum(w * conf_tactic) / sum(w)   over the 13 w > 0 pairs

Three choices carry the meaning:

  geometric mean over the two confidences
      A pair is only as strong as its weaker half, and the square root is what
      keeps the result on the same scale as conf_func: the plain product is not
      a mean, and would score two half-verified tactics 0.25 instead of 0.5.

  hyperbolic proximity 1/(1+d), not an exponential
      It separates the two shapes an exponential in d-1 conflates. Two tactics
      written into the *same* function score 1.0; one calling the other scores
      0.5. Only the first means the agent had to reconcile them in one body of
      code.

  max over function pairs
      An existential claim with a witness. A score of 0.5 does not say "the
      average entanglement is 0.5", it says *this* function calls *that* one —
      a reviewer can open both files and dispute it. A mean has no witness to
      point at, is diluted by unrelated distances, and drops when a tactic's
      implementation is duplicated. The cost is that max cannot see how
      pervasive an entanglement is, only how close it gets.

What this measures is EXPOSURE, not impact. A high score says two conflicting
tactics were implemented on interacting code paths — it does not say latency
rose or consistency broke, and it is not "worse architecture". Invalidating a
cache immediately after a commit scores high and is correct design. Whether the
agent recognised and resolved the tension is a question for the ADR and runtime
evidence, not for this number.

Conformance — how much of the requested tactic set is present at all — is NOT
computed here. It is stage 3's score_func / score_tactic / score_qa hierarchy,
and TICS deliberately never folds it in: one says how much was built, the other
how entangled what was built is, and a single number would let a thin
implementation pass as a clean architecture.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from math import sqrt
from pathlib import Path

from validators.tics.contract import TacticBinding
from validators.tics.model import CodeGraph

DEFAULT_MAX_DISTANCE = 6
_DATA = Path(__file__).parent / "data" / "conf_tacticset.json"


def proximity(distance: int | None) -> float:
    """1/(1+d): 1.0 for one function implementing both tactics, 0.5 for a direct
    call, 0.33 for a shared caller, 0.0 when they never meet."""
    if distance is None or distance < 0:
        return 0.0
    return 1.0 / (1.0 + distance)


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
    """One tactic pair's score, with the witness that produced it.

    The witness is the point of the max: `f_a`, `f_b` and `path` name the exact
    place in the code the score is claiming, so a reader can check it.
    """

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
class RepositoryScore:
    tics: float
    scoring_pairs: list[PairScore]
    synergy_pairs: list[PairScore]
    unclaimed_nfrs: list[str] = field(default_factory=list)

    @property
    def pairs_found(self) -> int:
        """Conflicting pairs that meet anywhere in the code. Reported as a plain
        count beside TICS, never folded into it: TICS is dominated by this
        number, so hiding it would let a value be read as intensity when it is
        largely coverage.
        """
        return sum(1 for p in self.scoring_pairs if p.found)


def _by_nfr(bindings: list[TacticBinding]) -> dict[str, list[TacticBinding]]:
    grouped: dict[str, list[TacticBinding]] = {}
    for binding in bindings:
        grouped.setdefault(binding.nfr_id, []).append(binding)
    return grouped


def conf_pair(s_a: float, s_b: float, distance: int | None) -> float:
    """sqrt(conf_func * conf_func) / (1 + d) for one candidate function pair."""
    return sqrt(s_a * s_b) * proximity(distance)


def pair_score(
    graph: CodeGraph,
    bindings: list[TacticBinding],
    nfr_a: str,
    nfr_b: str,
    *,
    weight: float = 1.0,
    max_distance: int = DEFAULT_MAX_DISTANCE,
) -> PairScore:
    """conf_tactic(t1,t2): the closest place the two tactics meet."""
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
                    value=conf_pair(a.s, b.s, path.distance),
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

    # Ties happen — a direct call between two fully verified functions and one
    # half-verified function implementing both tactics both score 0.5. Prefer the
    # shorter distance, because one function doing both jobs is the tighter
    # structural evidence, then order by ref so the reported witness is the same
    # on every run.
    candidates.sort(key=lambda c: (-c.value, c.distance, c.f_a, c.f_b))
    return candidates[0]


def score_repository(
    graph: CodeGraph,
    bindings: list[TacticBinding],
    conf: ConfTacticSet | None = None,
    *,
    max_distance: int = DEFAULT_MAX_DISTANCE,
) -> RepositoryScore:
    conf = conf or load_conf_tacticset()
    grouped = _by_nfr(bindings)

    def score(pairs: list[tuple[str, str]]) -> list[PairScore]:
        return [
            pair_score(
                graph, bindings, a, b,
                weight=conf.weight(a, b), max_distance=max_distance,
            )
            for a, b in sorted(pairs)
        ]

    scoring = score(conf.scoring_pairs)
    synergy = score(conf.support_pairs)

    # A pair whose tactics never meet contributes 0 to the numerator and its full
    # weight to the denominator: "these two were built and kept apart" is a real
    # architectural outcome, not a missing measurement.
    total = sum(p.weight for p in scoring)
    tics = sum(p.weight * p.value for p in scoring) / total if total else 0.0

    return RepositoryScore(
        tics=tics,
        scoring_pairs=scoring,
        synergy_pairs=synergy,
        # An NFR with no binding cannot participate in any pair. Reporting it
        # stops a trace that simply omits a tactic from reading as "no conflict".
        unclaimed_nfrs=[n for n in conf.nfr_names if n not in grouped],
    )
