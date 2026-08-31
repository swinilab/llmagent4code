import ast
import json
from pathlib import Path

import yaml

from app.main import app

ROOT = Path(__file__).resolve().parents[1]


def test_create_manifest_has_exact_entities_and_routes() -> None:
    manifest = json.loads((ROOT / "create_apis.json").read_text(encoding="utf-8"))
    assert set(manifest) == {"customer", "order", "product", "payment", "invoice"}
    for entity, definition in manifest.items():
        assert definition["method"] == "POST"
        assert definition["path"] == f"/api/v1/{entity}s"


def test_create_manifest_matches_runtime_openapi() -> None:
    manifest = json.loads((ROOT / "create_apis.json").read_text(encoding="utf-8"))
    paths = app.openapi()["paths"]
    for definition in manifest.values():
        operation = paths[definition["path"]][definition["method"].lower()]
        assert "201" in operation["responses"]
        assert f"{definition['path']}/{{" in "\n".join(paths)


def test_committed_openapi_matches_runtime_schema() -> None:
    committed = yaml.safe_load((ROOT / "openapi.yaml").read_text(encoding="utf-8"))
    assert committed == app.openapi()


def test_nfr_trace_references_existing_nontrivial_symbols() -> None:
    trace = json.loads((ROOT / "nfr-trace.json").read_text(encoding="utf-8"))["nfrTrace"]
    assert len(trace) == 6
    for entry in trace:
        for relative_path in entry["filesImplemented"]:
            assert (ROOT / relative_path).is_file()
        for reference in entry["functionNames"]:
            relative_path, function_name = reference.split("::", 1)
            tree = ast.parse((ROOT / relative_path).read_text(encoding="utf-8"))
            names = {node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
            assert function_name.rsplit(".", 1)[-1] in names


def test_start_command_is_exactly_one_nonempty_command() -> None:
    lines = [line for line in (ROOT / "start_command.txt").read_text().splitlines() if line.strip()]
    assert lines == ["docker compose up --build -d"]
