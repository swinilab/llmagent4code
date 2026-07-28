"""
QA tactic verifier.

Detects whether generated code adopts known architectural tactics, by looking
for (a) imports of tactic-associated libraries and (b) calls into those
libraries' API surfaces.

Three evidence levels per (file, library):
    0  ABSENT   - no import, no attributable API call
    1  IMPORT   - library imported but no API call attributable to it
    2  USED     - library imported AND >=1 API call attributable to it

Ground truth lives in tactics_spec.json and is HAND-WRITTEN, not derived from
demo snippets. Snippet-derived expectations are contaminated with scaffolding
(main, print, fetch_product) that no production file will ever contain.

Scope note: this measures observable ADOPTION of known implementations.
Level 2 means the API was called, not that the tactic is correctly configured
or wired into a live call path. A CircuitBreaker with an infinite threshold
scores the same as a correct one. Dataflow verification is out of scope.
"""
import os
import ast
import json
import argparse
from datetime import datetime

import pandas as pd

LEVEL_NAMES = {0: "ABSENT", 1: "IMPORT", 2: "USED"}


class ModuleAnalyzer(ast.NodeVisitor):
    """
    Extracts, for a single module:
      - module_imports: top-level module names that were imported
      - alias_to_module: local name -> originating top-level module
            import redis                  -> {"redis": "redis"}
            import redis as r             -> {"r": "redis"}
            import redis.asyncio as aio   -> {"aio": "redis"}
            from redis import Redis       -> {"Redis": "redis"}
            from redis import Redis as R  -> {"R": "redis"}
      - attr_calls: (receiver_root, attr) pairs, e.g. ("r", "setex")
      - bare_calls: plain names called, e.g. "Redis", "retry"
      - decorators: decorator names/attrs, since tactics are often applied
            via @retry, @circuit, @cached rather than an explicit call node
    """

    def __init__(self) -> None:
        self.module_imports: set[str] = set()
        self.alias_to_module: dict[str, str] = {}
        self.attr_calls: set[tuple[str, str]] = set()
        self.bare_calls: set[str] = set()
        self.decorators: set[str] = set()
        # attribute name -> originating module, for `self._queue = asyncio.Queue()`
        self.attr_bindings: dict[str, str] = {}

    # -- imports ----------------------------------------------------------
    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            root = alias.name.split(".")[0]
            self.module_imports.add(root)
            local = alias.asname or alias.name.split(".")[0]
            self.alias_to_module[local] = root
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if not node.module or node.level:  # skip relative imports
            self.generic_visit(node)
            return
        root = node.module.split(".")[0]
        self.module_imports.add(root)
        for alias in node.names:
            local = alias.asname or alias.name
            self.alias_to_module[local] = root
        self.generic_visit(node)

    # -- calls ------------------------------------------------------------
    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        if isinstance(func, ast.Name):
            self.bare_calls.add(func.id)
        elif isinstance(func, ast.Attribute):
            root = self._root_name(func.value)
            if root is not None:
                self.attr_calls.add((root, func.attr))
            else:
                # receiver unresolvable (e.g. chained call) - record loosely
                self.attr_calls.add(("", func.attr))
            # also key on the immediate receiver attribute, so
            # `self._queue.put_nowait()` can resolve via attr_bindings["_queue"]
            if isinstance(func.value, ast.Attribute):
                self.attr_calls.add(("@" + func.value.attr, func.attr))
        self.generic_visit(node)

    # -- assignment propagation -------------------------------------------
    def visit_Assign(self, node: ast.Assign) -> None:
        """
        Propagate library binding one hop through assignment, so that
            client = redis.Redis(...)   /   client = Redis(...)
        makes a later `client.setex(...)` attributable to redis.

        Only direct call-result assignments are followed; this is deliberately
        shallow, not type inference.
        """
        origin = self._call_origin(node.value)
        if origin is not None:
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    self.alias_to_module.setdefault(tgt.id, origin)
                elif isinstance(tgt, ast.Attribute):
                    # self._queue = asyncio.Queue(...)
                    self.attr_bindings[tgt.attr] = origin
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.value is not None:
            origin = self._call_origin(node.value)
            if origin is not None:
                if isinstance(node.target, ast.Name):
                    self.alias_to_module.setdefault(node.target.id, origin)
                elif isinstance(node.target, ast.Attribute):
                    self.attr_bindings[node.target.attr] = origin
        self.generic_visit(node)

    def _call_origin(self, value) -> str | None:
        """Top-level module a call expression originates from, if resolvable."""
        if not isinstance(value, ast.Call):
            return None
        func = value.func
        if isinstance(func, ast.Attribute):
            root = self._root_name(func.value)
        elif isinstance(func, ast.Name):
            root = func.id
        else:
            return None
        return self.alias_to_module.get(root) if root else None

    # -- decorators -------------------------------------------------------
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._collect_decorators(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._collect_decorators(node)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._collect_decorators(node)
        self.generic_visit(node)

    def _collect_decorators(self, node) -> None:
        for dec in node.decorator_list:
            target = dec.func if isinstance(dec, ast.Call) else dec
            if isinstance(target, ast.Name):
                self.decorators.add(target.id)
            elif isinstance(target, ast.Attribute):
                self.decorators.add(target.attr)
                root = self._root_name(target.value)
                if root is not None:
                    self.attr_calls.add((root, target.attr))

    @staticmethod
    def _root_name(expr) -> str | None:
        """Walk an attribute chain down to its base Name, if any."""
        while isinstance(expr, ast.Attribute):
            expr = expr.value
        return expr.id if isinstance(expr, ast.Name) else None


def analyze(code: str) -> ModuleAnalyzer | None:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    analyzer = ModuleAnalyzer()
    analyzer.visit(tree)
    return analyzer


def evaluate_library(an: ModuleAnalyzer, imports: list[str], api: list[str]):
    """
    Return (level, matched_api_names).

    An API call counts only if attributable to the library:
      - attribute call whose receiver root aliases back to the library, OR
      - bare call / decorator whose name was imported from the library
        (covers `from redis import Redis` then `Redis(...)`, and `@retry`)

    When the spec has no import names (hand-rolled fallbacks), name matching
    alone is used and the result is capped at level 1 to reflect weaker
    evidence.
    """
    api_set = set(api)
    import_set = set(imports)

    if not import_set:  # hand-rolled / naming-convention fallback
        hits = {
            name for name in api_set
            if name in an.bare_calls
            or name in an.decorators
            or any(attr == name for _, attr in an.attr_calls)
        }
        # capped at 1: name-only evidence, no import to attribute it to
        return (1 if hits else 0), sorted(hits)

    imported = bool(an.module_imports & import_set)
    if not imported:
        return 0, []

    # local names bound to this library
    local_names = {
        local for local, mod in an.alias_to_module.items() if mod in import_set
    }

    # attributes bound to this library, e.g. self._queue = asyncio.Queue()
    bound_attrs = {
        "@" + name for name, mod in an.attr_bindings.items() if mod in import_set
    }

    hits: set[str] = set()
    for root, attr in an.attr_calls:
        if attr in api_set and (root in local_names or root in bound_attrs):
            hits.add(attr)
    for name in an.bare_calls | an.decorators:
        if name in local_names and name in api_set:
            hits.add(name)

    return (2 if hits else 1), sorted(hits)


def load_spec(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)["nfrs"]


def collect_py_files(target_dir: str) -> list[str]:
    skip = {".venv", "venv", "__pycache__", ".git", "node_modules", "site-packages"}
    found = []
    for root, dirs, files in os.walk(target_dir):
        dirs[:] = [d for d in dirs if d not in skip]
        for f in files:
            if f.endswith(".py"):
                found.append(os.path.join(root, f))
    return sorted(found)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify architectural tactic adoption in generated code."
    )
    parser.add_argument("model", help="Label written to the 'model' column")
    parser.add_argument("--target-dir", default=None,
                        help="Folder to scan; overrides AIModelsEvaluation/<model>")
    parser.add_argument("--spec", default=None,
                        help="Path to tactics_spec.json (default: alongside this script)")
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)

    target_dir = os.path.abspath(
        args.target_dir or os.path.join(project_root, "AIModelsEvaluation", args.model)
    )
    spec_path = args.spec or os.path.join(script_dir, "tactics_spec.json")

    if not os.path.isdir(target_dir):
        print(f"Error: target directory does not exist: {target_dir}")
        return
    if not os.path.exists(spec_path):
        print(f"Error: spec file does not exist: {spec_path}")
        return

    nfrs = load_spec(spec_path)
    py_files = collect_py_files(target_dir)
    if not py_files:
        print(f"No .py files found under {target_dir}")
        return

    rows = []
    unparsed = []

    for py_file in py_files:
        rel = os.path.relpath(py_file, target_dir)
        with open(py_file, encoding="utf-8", errors="replace") as f:
            code = f.read()

        an = analyze(code)
        if an is None:
            unparsed.append(rel)
            continue

        for nfr in nfrs:
            entries = [
                (lib["library"], lib["imports"], lib["api"], "library")
                for lib in nfr["libraries"]
            ]
            fb = nfr.get("mechanism_fallback")
            if fb:
                entries.append((fb["label"], fb["imports"], fb["api"], "mechanism"))

            for label, imports, api, kind in entries:
                level, hits = evaluate_library(an, imports, api)
                if level == 0:
                    continue  # keep the report to positive evidence only
                rows.append({
                    "model": args.model,
                    "file_path": rel,
                    "nfr_id": nfr["nfr_id"],
                    "nfr_name": nfr["nfr_name"],
                    "mechanism": nfr["mechanism"],
                    "evidence_kind": kind,
                    "library": label,
                    "level": level,
                    "level_name": LEVEL_NAMES[level],
                    "matched_api": ";".join(hits),
                })

    cols = ["model", "file_path", "nfr_id", "nfr_name", "mechanism",
            "evidence_kind", "library", "level", "level_name", "matched_api"]
    detail = pd.DataFrame(rows, columns=cols)

    # -- project-level rollup: best evidence anywhere in the codebase -----
    summary_rows = []
    for nfr in nfrs:
        sub = detail[detail["nfr_id"] == nfr["nfr_id"]]
        lib_sub = sub[sub["evidence_kind"] == "library"]
        best = int(lib_sub["level"].max()) if not lib_sub.empty else 0
        mech_sub = sub[sub["evidence_kind"] == "mechanism"]
        summary_rows.append({
            "model": args.model,
            "nfr_id": nfr["nfr_id"],
            "nfr_name": nfr["nfr_name"],
            "mechanism": nfr["mechanism"],
            "best_level": best,
            "best_level_name": LEVEL_NAMES[best],
            "libraries_used": ";".join(sorted(lib_sub[lib_sub["level"] == 2]["library"].unique())),
            "libraries_imported_only": ";".join(sorted(lib_sub[lib_sub["level"] == 1]["library"].unique())),
            "mechanism_fallback_hit": bool(not mech_sub.empty),
            "evidence_files": ";".join(sorted(sub[sub["level"] == max(best, 1)]["file_path"].unique())[:5]),
        })
    summary = pd.DataFrame(summary_rows)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    detail_csv = os.path.join(script_dir, f"evidence_detail_{args.model}_{stamp}.csv")
    summary_csv = os.path.join(script_dir, f"evidence_summary_{args.model}_{stamp}.csv")
    detail.to_csv(detail_csv, index=False)
    summary.to_csv(summary_csv, index=False)

    print(f"Scanned {len(py_files)} file(s) under {target_dir}")
    if unparsed:
        print(f"Unparsed (syntax errors): {len(unparsed)} -> {', '.join(unparsed[:5])}")
    print()
    print(summary[["nfr_id", "mechanism", "best_level_name",
                   "libraries_used", "mechanism_fallback_hit"]].to_string(index=False))
    print()
    print(f"Detail : {detail_csv}")
    print(f"Summary: {summary_csv}")


if __name__ == "__main__":
    main()
