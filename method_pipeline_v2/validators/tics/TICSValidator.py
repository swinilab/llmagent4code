"""
TICSValidator.py
────────────────
Tactic Interaction Conflict Score, as a pipeline stage.

Measures how far an implementation places tactics that are known to pull against
each other. It answers "where do these conflicts materialise in this code", not
"did the agent handle them well" — a high score is not a defect. Cache
invalidation next to a transaction is correct design; the score locates it so
that ADR and runtime evidence can say whether the agent knew.

Two numbers are reported side by side and never combined:

    TICS         conflict among what the repository actually built. HIGH IS BAD.
    conformance  how much of the fixed tactic set is substantively present.
                 HIGH IS GOOD.

Both are needed because they can be gamed in opposite directions. TICS is
conditioned on implementation — a pair leaves the calculation when either tactic
is absent — so building less no longer buys a good score; and conformance is
never folded in, so a thin implementation cannot pass as a clean architecture.
On the first sample the agent with the lowest TICS also had the worst
conformance, and reading TICS alone would have called it the best design.

The stage refuses to score a repository whose nfr-trace.json describes a
different NFR set. Ids alone are not a safe join: earlier prompt generations
reused "NFR 1.2" for a different requirement, and scoring one against the
other's ground truth yields a plausible number that means nothing.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from interfaces.base import (
    GenerationResult,
    Status,
    ValidationResult,
    app_run_dir,
)
from validators.tics.contract import (
    ITacticBindingProvider,
    TraceOnlyBindingProvider,
    dump_bindings,
    nfr_set_mismatches,
    read_trace_labels,
)
from validators.tics.extractors.base import select_extractor
from validators.tics.static_qa_provider import StaticQABindingProvider
from validators.tics.model import CALLS
from validators.tics.scoring import load_conf_tacticset, score_repository


class TICSValidator:
    """Stage 5 — static conflict exposure between competing tactics."""

    def __init__(
        self,
        config: dict | None = None,
        binding_provider: ITacticBindingProvider | None = None,
    ) -> None:
        config = config or {}
        validator_cfg = config.get("validator", {})
        self._trace_filename = validator_cfg.get("nfr_trace_filename", "nfr-trace.json")
        self._report_dir = Path(config.get("output", {}).get("report_dir", "reports/"))
        self._source_roots = validator_cfg.get("tics_source_roots")     # None -> infer
        # Injected so a change to how stage 3 computes S(x,f) is picked up here
        # with no edit. Left unset, stage 3's report is used when one exists for
        # this repository and the trace-only fallback otherwise — the fallback
        # pins every confidence to 1.0, so it announces itself as degraded rather
        # than quietly producing numbers that look the same but are not.
        self._provider = binding_provider
        self._report_dir_for_provider = self._report_dir
        self._conf = load_conf_tacticset()

    def validate(self, generation_result: GenerationResult) -> ValidationResult:
        repo_root = Path(generation_result.code).resolve()

        trace_path = repo_root / self._trace_filename
        if not trace_path.is_file():
            return self._fail(f"NFR trace file not found: {trace_path}", {"error": "FileNotFoundError"})

        mismatches = nfr_set_mismatches(
            read_trace_labels(repo_root, self._trace_filename), self._conf.nfr_names
        )
        if mismatches:
            return self._fail(
                f"trace describes a different NFR set ({len(mismatches)} mismatch(es)); "
                "refusing to score against ground truth that does not apply",
                {"nfrSetMismatches": mismatches},
            )

        try:
            extractor = select_extractor(repo_root)
        except NotImplementedError as exc:
            return self._fail(str(exc), {"error": "UnsupportedLanguage"})

        graph = extractor.build_graph(repo_root, self._source_roots)
        bindings, provider_note = self._load_bindings(repo_root)
        result = score_repository(graph, bindings)

        missing = [b.function_ref for b in bindings if b.function_ref not in graph]
        degraded = any(b.evidence.get("degraded") for b in bindings)

        report_path, graph_path, bindings_path = self._write_report(
            repo_root, extractor, graph, result, bindings, missing, degraded
        )

        message = (
            f"TICS {result.tics:.3f} (high=worse) | "
            f"conformance {result.conformance:.3f} (high=better) | "
            f"{sum(1 for p in result.scoring_pairs if p.found)}/"
            f"{len(result.scoring_pairs)} pairs interacting, "
            f"{result.applicable_mass:.0%} of ground truth applicable"
        )
        if degraded:
            message += f"  [DEGRADED: S=1.0 for every function ({provider_note}), not publishable]"
        # Named in the message, not only in the details dict: this stage is run
        # by hand to work out why a pair scored what it did, and the graph is the
        # artefact you open to find out.
        message += "\n".join([
            "",
            f"    graph    {graph_path}"
            f"  ({len(graph)} nodes, {len(graph.edges)} edges,"
            f" {graph.unresolved_calls} unresolved calls)",
            f"    report   {report_path}",
            f"    bindings {bindings_path}",
        ])

        # Exposure is a measurement, not a defect: there is no threshold at which
        # a repository "fails" TICS. The stage passes whenever it produced a
        # score, and fails only when it could not.
        return ValidationResult(
            stage="tics",
            status=Status.PASS,
            message=message,
            details={
                "tics": round(result.tics, 4),
                "conformance": round(result.conformance, 4),
                "applicableMass": round(result.applicable_mass, 4),
                "implementation": {k: round(v, 4) for k, v in result.implementation.items()},
                "breadth": round(result.breadth, 4),
                "intensity": round(result.intensity, 4),
                "coverage": round(result.coverage, 4),
                "proximityLift": result.proximity_lift,
                "degraded": degraded,
                "claimedFunctionsMissingFromGraph": missing,
                # All three are written every run and named here rather than only
                # inside the report, because the graph is the artefact you open
                # when a score looks wrong and the scores alone cannot say why.
                "reportPath": report_path,
                "run_dir": str(Path(report_path).parent),
                "graphPath": graph_path,
                "bindingsPath": bindings_path,
            },
        )

    def _load_bindings(self, repo_root: Path):
        """Prefer stage 3's measured confidences; say so when falling back."""
        if self._provider is not None:
            return self._provider.bindings(repo_root), "provider injected"
        try:
            provider = StaticQABindingProvider(report_dir=self._report_dir_for_provider)
            return provider.bindings(repo_root), "stage 3 report"
        except (FileNotFoundError, ValueError) as exc:
            return TraceOnlyBindingProvider().bindings(repo_root), f"no stage 3 report: {exc}"

    # ── reporting ───────────────────────────────────────────────────────────
    def _write_report(
        self, repo_root, extractor, graph, result, bindings, missing, degraded
    ) -> tuple[str, str, str]:
        """Write the three artefacts of a run and return their paths.

        The graph and the bindings are not optional extras: together they are
        everything the score was computed from, so a reported number can be
        re-derived — or disputed — without re-running the extractor.
        """
        run_dir = app_run_dir(self._report_dir, "tics", repo_root)
        path = run_dir / "tics_report.json"

        payload = {
            "generatedAt": datetime.now().isoformat(timespec="seconds"),
            "repoRoot": str(repo_root),
            "language": extractor.language,
            "degraded": degraded,
            "score": {
                "tics": round(result.tics, 4),
                "conformance": round(result.conformance, 4),
                "applicableMass": round(result.applicable_mass, 4),
                "implementationByNfr": {k: round(v, 4) for k, v in result.implementation.items()},
                "breadth": round(result.breadth, 4),
                "intensity": round(result.intensity, 4),
                "coverage": round(result.coverage, 4),
                "medianConflictDistance": result.median_conflict_distance,
                "proximityLift": result.proximity_lift,
                "meanPair": round(result.mean_pair, 4),
                "maxPair": round(result.max_pair, 4),
            },
            "baseline": (
                {
                    "medianDistance": result.baseline.median_distance,
                    "meanDistance": round(result.baseline.mean_distance, 3),
                    "reachableFraction": round(result.baseline.reachable_fraction, 4),
                    "sampleSize": result.baseline.sample_size,
                }
                if result.baseline
                else None
            ),
            "graph": {
                "nodes": len(graph),
                "edges": {CALLS: len(graph.edges_of_kind(CALLS))},
                # Only `unresolved` is a gap; external and nodeless targets have
                # no node by design. Reported so a reader can judge how complete
                # the graph behind these scores actually is.
                "externalCalls": graph.external_calls,
                "nodelessCalls": graph.nodeless_calls,
                "unresolvedCalls": graph.unresolved_calls,
            },
            "trace": {
                "claimedFunctions": len({b.function_ref for b in bindings}),
                "missingFromGraph": missing,
                "unclaimedNfrs": result.unclaimed_nfrs,
            },
            "pairs": [self._pair_row(p) for p in result.scoring_pairs],
            # Support pairs are measured but never scored: penalising an agent
            # for using one mechanism to serve two co-operating tactics would
            # reward worse design.
            "synergyPairs": [self._pair_row(p) for p in result.synergy_pairs],
        }
        # The full graph, alongside the scores it produced. Without it the report
        # asserts distances a reader has no way to check: every score here is a
        # function of edges that would otherwise exist only in memory. Written
        # every run, and re-loadable via CodeGraph.from_dict.
        graph_path = path.with_name("tics_graph.json")
        graph_payload = graph.to_dict()
        graph_payload["repoRoot"] = str(repo_root)
        graph_payload["language"] = extractor.language
        graph_payload["sourceRoots"] = self._source_roots or extractor.infer_source_roots(repo_root)
        graph_path.write_text(
            json.dumps(graph_payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        payload["graph"]["dumpPath"] = str(graph_path)

        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

        # Bindings are dumped every run too, not only when degraded: reproducing
        # a reported TICS months later needs the exact S values it was built on.
        bindings_path = path.with_name("tics_bindings.json")
        dump_bindings(bindings, bindings_path, repo_root)
        return str(path), str(graph_path), str(bindings_path)

    @staticmethod
    def _pair_row(pair) -> dict:
        return {
            "pair": list(pair.pair),
            "weight": pair.weight,
            "score": round(pair.value, 4),
            "distance": pair.distance,
            "functionA": pair.f_a,
            "functionB": pair.f_b,
            "path": pair.path,
            "edgeKinds": pair.kinds,
        }

    def _fail(self, message: str, details: dict) -> ValidationResult:
        return ValidationResult(stage="tics", status=Status.FAIL, message=message, details=details)
