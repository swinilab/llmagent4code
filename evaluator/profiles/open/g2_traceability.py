"""G2 (open profile) -- traceability without a prescribed tactic vocabulary.

The prescriptive profile can compare `tacticUsed` against six exact strings,
because its prompt supplies them. The open prompt supplies definitions instead
and asks the agent to "cite real tactic names from Bass/Clements/Kazman" -- so
the check here is structural rather than literal: does the cited name belong to
the published taxonomy, and does it sit in the branch the NFR's definition
describes?

That is a weaker check, and deliberately so. An agent that reaches Timeout by
naming it `Availability > Detect Faults > Timeout` and one that writes
`Detect Faults / Timeout` have both cited the taxonomy correctly; failing the
second for punctuation would measure formatting, not architecture.

The manifest and source-resolution checks are the same questions the
prescriptive profile asks, delegated to `common/` so the two profiles cannot
drift apart on what "the function exists" means.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ...common import manifest_check, trace_check
from ...report.schema import Assertion, Evidence, GateResult, assert_that

# The Availability and Performance tactic trees, as published. Leaf names are
# what an agent cites; the branch is what pins the citation to the right part
# of the taxonomy.
TACTIC_TREE: dict[str, dict[str, list[str]]] = {
    "availability": {
        "detect faults": [
            "monitor", "ping/echo", "heartbeat", "timestamp", "condition monitoring",
            "sanity checking", "voting", "exception detection", "self-test",
            # Timeout is a Detect Faults tactic; the open prompt's NFR 2.1
            # states it directly, so a citation naming it must resolve.
            "timeout",
        ],
        "recover from faults": [
            "redundant spare", "rollback", "exception handling", "software upgrade",
            "retry", "ignore faulty behavior", "graceful degradation", "reconfiguration",
            "shadow", "state resynchronization", "escalating restart", "nonstop forwarding",
        ],
        "prevent faults": [
            "removal from service", "transactions", "predictive model",
            "exception prevention", "increase competence set",
        ],
    },
    "performance": {
        "control resource demand": [
            "manage sampling rate", "limit event response", "prioritize events",
            "reduce overhead", "bound execution times", "increase resource efficiency",
        ],
        "manage resources": [
            "increase resources", "introduce concurrency", "maintain multiple copies of computations",
            "maintain multiple copies of data", "bound queue sizes", "schedule resources",
        ],
    },
}

REQUIRED_ENTRY_KEYS = ("nfr", "tacticUsed", "filesImplemented", "functionNames", "librariesUsed")


@dataclass
class TraceIssue:
    nfr: str
    kind: str
    detail: str


@dataclass
class TraceAudit:
    entries: list[dict[str, Any]] = field(default_factory=list)
    issues: list[TraceIssue] = field(default_factory=list)
    resolved: dict[str, int] = field(default_factory=lambda: {
        "files": 0, "files_missing": 0, "functions": 0, "functions_missing": 0,
        "library_corroborated": 0, "library_uncorroborated": 0,
    })


def run(
    app_dir: Path,
    expected_nfrs: list[str],
    domain_entities: list[str],
    minimum_workflow_steps: int,
) -> GateResult:
    assertions: list[Assertion] = []
    details: dict[str, Any] = {}

    audit = _audit_trace(app_dir, expected_nfrs)
    assertions += _trace_assertions(audit, expected_nfrs)
    details["traceability_issues"] = [vars(i) for i in audit.issues]
    details["resolved_references"] = audit.resolved

    create = manifest_check.check_create_manifest(
        app_dir, domain_entities, require_read_template=True
    )
    workflow = manifest_check.check_workflow_manifest(app_dir, minimum_workflow_steps)

    assertions.append(
        assert_that(
            "create_apis.json declares every entity with an explicit read template",
            create.ok,
            f"{len(domain_entities)} usable entries",
            "; ".join(f"{i.key}: {i.detail}" for i in create.issues) or "all usable",
            evidence=Evidence.ARTIFACT,
        )
    )
    assertions.append(
        assert_that(
            "workflow_apis.json declares every state-changing step",
            workflow.ok,
            f"at least {minimum_workflow_steps} invocable steps",
            "; ".join(f"{i.key}: {i.detail}" for i in workflow.issues) or "all invocable",
            evidence=Evidence.ARTIFACT,
        )
    )
    details["manifests"] = {
        "create": {"entries": list(create.entries), "issues": [vars(i) for i in create.issues]},
        "workflow": {"entries": list(workflow.entries), "issues": [vars(i) for i in workflow.issues]},
    }

    return GateResult("G2", all(a.passed for a in assertions), assertions, details)


def _audit_trace(app_dir: Path, expected_nfrs: list[str]) -> TraceAudit:
    audit = TraceAudit()

    path = app_dir / "nfr-trace.json"
    if not path.is_file():
        audit.issues.append(TraceIssue("-", "absent", "nfr-trace.json is missing"))
        return audit

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        entries = data["nfrTrace"]
        if not isinstance(entries, list):
            raise TypeError("nfrTrace is not a list")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        audit.issues.append(TraceIssue("-", "unparseable", str(exc)[:200]))
        return audit

    audit.entries = [e for e in entries if isinstance(e, dict)]

    for entry in audit.entries:
        nfr = str(entry.get("nfr", "")).strip() or "(unnamed)"

        for key in REQUIRED_ENTRY_KEYS:
            if key not in entry:
                audit.issues.append(TraceIssue(nfr, "missing_key", key))

        claimed = str(entry.get("tacticUsed", ""))
        problem = _tactic_problem(claimed)
        if problem:
            audit.issues.append(TraceIssue(nfr, "tactic_not_in_taxonomy", problem))

        for rel in entry.get("filesImplemented") or []:
            if (app_dir / str(rel)).is_file():
                audit.resolved["files"] += 1
            else:
                audit.resolved["files_missing"] += 1
                audit.issues.append(TraceIssue(nfr, "file_not_found", str(rel)))

        libraries = [str(lib) for lib in (entry.get("librariesUsed") or []) if str(lib).strip()]
        for ref in entry.get("functionNames") or []:
            reference = str(ref)
            if not trace_check.function_exists(app_dir, reference):
                audit.resolved["functions_missing"] += 1
                audit.issues.append(TraceIssue(nfr, "function_not_found", reference))
                continue

            audit.resolved["functions"] += 1
            # The prompt asks for the function that calls into the claimed
            # mechanism, not the handler that calls that function. Where a
            # library is named, look for it in the cited function's own body.
            if libraries:
                if trace_check.function_mentions(app_dir, reference, libraries):
                    audit.resolved["library_corroborated"] += 1
                else:
                    audit.resolved["library_uncorroborated"] += 1
                    audit.issues.append(
                        TraceIssue(nfr, "library_not_visible_in_function",
                                   f"{reference} does not mention {libraries}")
                    )

    return audit


def _trace_assertions(audit: TraceAudit, expected_nfrs: list[str]) -> list[Assertion]:
    out: list[Assertion] = []

    named = {str(e.get("nfr", "")).strip() for e in audit.entries}
    missing = [n for n in expected_nfrs if not _covered(n, named)]
    out.append(
        assert_that(
            "one traceability entry per NFR",
            not missing,
            f"{len(expected_nfrs)} entries",
            f"missing: {missing}" if missing else f"{len(audit.entries)} present",
            evidence=Evidence.ARTIFACT,
        )
    )

    taxonomy_issues = [i for i in audit.issues if i.kind == "tactic_not_in_taxonomy"]
    out.append(
        assert_that(
            "every cited tactic belongs to the published taxonomy",
            not taxonomy_issues,
            "all cited tactics resolvable",
            "; ".join(i.detail for i in taxonomy_issues) or "all resolvable",
            evidence=Evidence.ARTIFACT,
        )
    )

    out.append(
        assert_that(
            "every cited file resolves",
            audit.resolved["files_missing"] == 0,
            0, audit.resolved["files_missing"],
            evidence=Evidence.ARTIFACT,
            note=f"{audit.resolved['files']} resolved",
        )
    )
    out.append(
        assert_that(
            "every cited function resolves",
            audit.resolved["functions_missing"] == 0,
            0, audit.resolved["functions_missing"],
            evidence=Evidence.ARTIFACT,
            note=f"{audit.resolved['functions']} resolved; existence only, not effectiveness",
        )
    )
    out.append(
        assert_that(
            "cited functions visibly use the libraries they claim",
            audit.resolved["library_uncorroborated"] == 0,
            0, audit.resolved["library_uncorroborated"],
            evidence=Evidence.ARTIFACT,
            note="substring match over the function body; a miss means the entry likely "
                 "names a caller rather than the function reaching the mechanism",
        )
    )
    return out


def _tactic_problem(claimed: str) -> str:
    """Why a cited tactic fails to resolve against the taxonomy, or ''.

    Matching is lenient about separators and casing and strict about the leaf
    name, because the leaf is the architectural claim -- 'Graceful Degradation'
    and 'Degradation' are different tactics, while '>' and '/' are punctuation.
    """
    if not claimed.strip():
        return "no tactic cited"

    normalised = claimed.lower().replace(">", "/").replace("»", "/")
    segments = [s.strip() for s in normalised.split("/") if s.strip()]
    if not segments:
        return f"{claimed!r} has no usable segments"

    leaf = segments[-1]
    context = "/".join(segments[:-1])

    for quality, branches in TACTIC_TREE.items():
        for branch, leaves in branches.items():
            if leaf not in leaves:
                continue

            # The leaf is real. A citation may omit context entirely -- the
            # leaf alone is unambiguous across this taxonomy -- but whatever
            # context it does give has to be the right context. Naming a
            # quality attribute the tactic does not belong to, or a branch it
            # does not sit under, is a misplacement rather than a shorthand.
            named_quality = next(
                (q for q in TACTIC_TREE if q in context), None
            )
            if named_quality is not None and named_quality != quality:
                return (
                    f"{claimed!r} places {leaf!r} under {named_quality}, but it is a "
                    f"{quality} tactic"
                )

            named_branch = next(
                (b for qb in TACTIC_TREE.values() for b in qb if b in context), None
            )
            if named_branch is not None and named_branch != branch:
                return (
                    f"{claimed!r} places {leaf!r} under {named_branch!r}, but it sits "
                    f"under {branch!r}"
                )
            return ""

    return f"{claimed!r} ends in {leaf!r}, which is not a tactic in the taxonomy"


def _covered(nfr: str, named: set[str]) -> bool:
    token = _identifier(nfr)
    return any(_identifier(n) == token for n in named)


def _identifier(label: str) -> str:
    for part in label.replace("-", " ").split():
        if part[:1].isdigit() and "." in part:
            return part.strip(".:")
    return label.strip().lower()
