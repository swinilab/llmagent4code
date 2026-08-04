"""Validating the API manifests a submission declares.

The manifests are the only channel through which the harness locates
endpoints: it does not read source, and it does not guess REST conventions. A
manifest that disagrees with the running routes therefore makes the submission
undriveable, which is a defect in its own right and not merely a documentation
slip.

Two manifests are handled:

  create_apis.json    one entry per domain entity: create path, and -- in the
                      open profile -- an explicit single-resource read template
  workflow_apis.json  one entry per state-changing workflow step, with the
                      precondition state that step requires

Both are checked against `/openapi.json` from the running application, so the
question answered is "do the declared routes exist where the app says they do",
not "does the file parse".
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Matches the {id} placeholder a path template must contain.
PLACEHOLDER = re.compile(r"\{([^}]+)\}")


@dataclass
class ManifestIssue:
    manifest: str
    key: str
    kind: str
    detail: str


@dataclass
class ManifestCheck:
    entries: dict[str, dict[str, Any]] = field(default_factory=dict)
    issues: list[ManifestIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.issues


def load(app_dir: Path, filename: str) -> tuple[dict[str, Any] | None, str]:
    """Read a manifest, returning (contents, error). Exactly one is truthy."""
    path = app_dir / filename
    if not path.is_file():
        return None, f"{filename} is absent"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return None, f"{filename} is not valid JSON: {str(exc)[:200]}"
    if not isinstance(data, dict):
        return None, f"{filename} must be a JSON object keyed by name"
    return data, ""


def check_create_manifest(
    app_dir: Path,
    expected_entities: list[str],
    *,
    require_read_template: bool,
) -> ManifestCheck:
    """Validate create_apis.json.

    `require_read_template` distinguishes the profiles. The prescriptive prompt
    fixes the routes itself, so the harness can append '/{id}'. The open prompt
    lets the agent choose its routing, so the read path must be declared -- and
    assuming it would silently mis-score an application whose read route is
    shaped differently but entirely correct.
    """
    result = ManifestCheck()
    data, error = load(app_dir, "create_apis.json")
    if data is None:
        result.issues.append(ManifestIssue("create_apis.json", "-", "unreadable", error))
        return result

    for entity in expected_entities:
        entry = data.get(entity)
        if not isinstance(entry, dict):
            result.issues.append(
                ManifestIssue("create_apis.json", entity, "missing_entry",
                              "no object declared for this domain entity")
            )
            continue

        method = str(entry.get("method", "")).upper()
        if method != "POST":
            result.issues.append(
                ManifestIssue("create_apis.json", entity, "wrong_method",
                              f"expected POST, declared {method or '(absent)'}")
            )

        path = str(entry.get("path", ""))
        if not path.startswith("/"):
            result.issues.append(
                ManifestIssue("create_apis.json", entity, "bad_path",
                              f"expected a rooted path, declared {path or '(absent)'}")
            )
        elif PLACEHOLDER.search(path):
            result.issues.append(
                ManifestIssue("create_apis.json", entity, "bad_path",
                              f"create path must not contain a placeholder: {path}")
            )

        if require_read_template:
            template = str(entry.get("readPathTemplate", ""))
            problem = _template_problem(template)
            if problem:
                result.issues.append(
                    ManifestIssue("create_apis.json", entity, "bad_read_template", problem)
                )

        result.entries[entity] = entry

    unexpected = [k for k in data if k not in expected_entities]
    if unexpected:
        result.issues.append(
            ManifestIssue("create_apis.json", ",".join(sorted(unexpected)), "unexpected_entry",
                          "keys not corresponding to a domain entity")
        )
    return result


def check_workflow_manifest(app_dir: Path, minimum_steps: int) -> ManifestCheck:
    """Validate workflow_apis.json.

    Step names are the agent's to choose -- the prompt derives them from the
    Behavior Workflow rather than fixing a vocabulary -- so nothing here checks
    names against a list. What is checked is that each entry is invocable: a
    verb, a template with exactly one placeholder, and a declared precondition
    the harness can drive a 409 probe against.
    """
    result = ManifestCheck()
    data, error = load(app_dir, "workflow_apis.json")
    if data is None:
        result.issues.append(ManifestIssue("workflow_apis.json", "-", "unreadable", error))
        return result

    for name, entry in data.items():
        if not isinstance(entry, dict):
            result.issues.append(
                ManifestIssue("workflow_apis.json", name, "bad_entry", "not an object")
            )
            continue

        method = str(entry.get("method", "")).upper()
        if method not in {"POST", "PUT", "PATCH"}:
            result.issues.append(
                ManifestIssue("workflow_apis.json", name, "wrong_method",
                              f"a state-changing step needs POST/PUT/PATCH, declared "
                              f"{method or '(absent)'}")
            )

        problem = _template_problem(str(entry.get("pathTemplate", "")))
        if problem:
            result.issues.append(
                ManifestIssue("workflow_apis.json", name, "bad_path_template", problem)
            )

        if not str(entry.get("precondition", "")).strip():
            result.issues.append(
                ManifestIssue("workflow_apis.json", name, "missing_precondition",
                              "no precondition declared, so no 409 probe can be constructed")
            )

        result.entries[name] = entry

    if len(data) < minimum_steps:
        result.issues.append(
            ManifestIssue("workflow_apis.json", "-", "too_few_steps",
                          f"the workflow describes at least {minimum_steps} state-changing "
                          f"steps, {len(data)} declared")
        )
    return result


def _template_problem(template: str) -> str:
    """Why a path template is unusable, or '' when it is fine."""
    if not template:
        return "absent"
    if not template.startswith("/"):
        return f"expected a rooted path, declared {template}"
    placeholders = PLACEHOLDER.findall(template)
    if len(placeholders) != 1:
        return (
            f"expected exactly one placeholder, found {len(placeholders)}: {template}"
        )
    return ""


def declared_routes(manifest: dict[str, Any], path_key: str) -> set[tuple[str, str]]:
    """(method, path-with-placeholders-normalised) pairs declared in a manifest."""
    routes: set[tuple[str, str]] = set()
    for entry in manifest.values():
        if not isinstance(entry, dict):
            continue
        path = entry.get(path_key)
        method = entry.get("method")
        if isinstance(path, str) and isinstance(method, str):
            routes.add((method.upper(), _normalise(path)))
    return routes


def openapi_routes(document: dict[str, Any]) -> set[tuple[str, str]]:
    """(method, normalised path) pairs the running application actually serves."""
    routes: set[tuple[str, str]] = set()
    paths = document.get("paths")
    if not isinstance(paths, dict):
        return routes
    for path, operations in paths.items():
        if not isinstance(operations, dict):
            continue
        for method in operations:
            if method.upper() in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                routes.add((method.upper(), _normalise(str(path))))
    return routes


def _normalise(path: str) -> str:
    """Reduce placeholder names so {id} and {orderId} compare equal.

    The manifest and the OpenAPI document are written independently, and a
    parameter named differently in each is not a defect -- the harness
    substitutes positionally.
    """
    return PLACEHOLDER.sub("{}", path.rstrip("/")) or "/"
