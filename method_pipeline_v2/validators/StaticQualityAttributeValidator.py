"""
StaticQualityAttributeValidator.py
────────────────────────────────────
Stage 3 – NFR trace verifier — EXISTENCE checking (no behavior).

For each NFR entry, verify the trace's claims actually exist in the claimed files:
  1. RESOLVE   — is every claimed tactic a known tactic (catalog membership)?
  2. LOCATE    — do the claimed files exist, and do the claimed functions
                 exist inside them?
  3. FUNCTIONS — is each claimed function non-trivial (not an empty stub)?
  4. LIBRARIES — is each claimed library imported in a claimed file AND used
                 (referenced beyond its import statement)?

No behavioral detection. We do NOT check whether a function implements its
tactic — only that the claimed functions and libraries genuinely exist and are
non-empty / actually used. Weakest claim sets the entry verdict.

Verdicts: PRESENT / WEAK / ABSENT (+ OUT_OF_CATALOG at resolve).
  functions: exists+non-trivial=PRESENT, stub=WEAK, missing=ABSENT
  libraries: imported+used=PRESENT, imported-unused=WEAK, not-imported=ABSENT
"""

from __future__ import annotations

import ast
import json
from datetime import datetime
from pathlib import Path

from interfaces.base import (
    GenerationResult,
    IStaticQualityValidator,
    Status,
    ValidationResult,
)

HERE = Path(__file__).parent

# --- verdict labels ---
OK = "RESOLVED_OK"
ABSENT = "ABSENT"
WEAK = "WEAK"
PRESENT = "PRESENT"
OUT_OF_CATALOG = "OUT_OF_CATALOG"

# rank for combining: weakest wins
RANK = {ABSENT: 0, WEAK: 1, PRESENT: 2}


# ─────────────────────────────────────────────────────────────────────────────
#  Stateless parsing / analysis helpers (no I/O beyond reading source files)
# ─────────────────────────────────────────────────────────────────────────────
def _leaf_tactic(tactic_str):
    return tactic_str.split(">")[-1].strip()


def _split_tactics(tactic_field):
    return [_leaf_tactic(t) for t in tactic_field.split(";") if t.strip()]


def _parse_file(path):
    try:
        return ast.parse(Path(path).read_text(encoding="utf-8")), None
    except (SyntaxError, UnicodeDecodeError) as e:
        return None, f"parse error: {e}"


def _function_defs(tree):
    out = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.setdefault(node.name, node)
    return out


def _is_stub(func_node):
    """A function is a stub if its body is only: pass / ... / a docstring /
    raise NotImplementedError / a bare `return` or `return None`."""
    body = list(func_node.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
            and isinstance(body[0].value.value, str):
        body = body[1:]
    if not body:
        return True  # docstring only
    if len(body) == 1:
        only = body[0]
        if isinstance(only, ast.Pass):
            return True
        if isinstance(only, ast.Expr) and isinstance(only.value, ast.Constant) \
                and only.value.value is Ellipsis:
            return True
        if isinstance(only, ast.Raise):
            exc = only.exc
            name = ""
            if isinstance(exc, ast.Call):
                name = getattr(exc.func, "id", "") or getattr(exc.func, "attr", "")
            elif isinstance(exc, ast.Name):
                name = exc.id
            if name == "NotImplementedError":
                return True
        if isinstance(only, ast.Return) and (only.value is None or
                (isinstance(only.value, ast.Constant) and only.value.value is None)):
            return True
    return False


def _check_functions(entry, located):
    """Return a list of (ref, status, detail) per claimed function."""
    results = []
    for ref in entry.get("functionNames", []):
        rel, _, func = ref.partition("::")
        if rel not in located or func not in located[rel][1]:
            results.append((ref, ABSENT, "function not found"))
            continue
        node = located[rel][1][func]
        if _is_stub(node):
            results.append((ref, WEAK, "empty stub (pass/…/NotImplementedError/docstring only)"))
        else:
            results.append((ref, PRESENT, "non-trivial body"))
    return results


def _collect_imports(tree):
    """bound_name -> ('module', module_name) | ('from', module_name, orig_attr)."""
    imports = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                bound = alias.asname or alias.name.split(".")[0]
                imports[bound] = ("module", alias.name)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            for alias in node.names:
                bound = alias.asname or alias.name
                imports[bound] = ("from", mod, alias.name)
    return imports


def _name_used_outside_imports(tree, bound_name):
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        if isinstance(node, ast.Name) and node.id == bound_name:
            return True
        if isinstance(node, ast.Attribute):
            base = node
            while isinstance(base, ast.Attribute):
                base = base.value
            if isinstance(base, ast.Name) and base.id == bound_name:
                return True
    return False


def _attribute_path_used(tree, module_name, attr):
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == attr:
            base = node.value
            if isinstance(base, ast.Name) and base.id == module_name:
                return True
    return False


def _check_library(lib, located):
    top = lib.split(".")[0]
    member = lib.split(".")[1] if "." in lib else None
    imported_anywhere = False
    used = False
    for rel in located:
        tree = located[rel][0]
        imports = _collect_imports(tree)
        bounds = [b for b, spec in imports.items()
                  if spec[1].split(".")[0] == top]
        if not bounds:
            continue
        imported_anywhere = True
        if member:
            for b, spec in imports.items():
                if spec[0] == "from" and spec[1].split(".")[0] == top and spec[2] == member \
                        and _name_used_outside_imports(tree, b):
                    used = True
                if spec[0] == "module" and spec[1].split(".")[0] == top \
                        and _attribute_path_used(tree, b, member):
                    used = True
        else:
            if any(_name_used_outside_imports(tree, b) for b in bounds):
                used = True
    if not imported_anywhere:
        return ABSENT, f"'{lib}' not imported in any claimed file"
    if not used:
        return WEAK, f"'{lib}' imported but not used (dead import)"
    return PRESENT, f"'{lib}' imported and used"


def _check_libraries(entry, located):
    return [(lib, *_check_library(lib, located)) for lib in entry.get("librariesUsed", [])]


def _names_in_node(node):
    """Set of identifiers referenced in `node`: bare Names and the base of any
    Attribute chain (e.g. 'asyncio' in asyncio.Queue)."""
    names = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name):
            names.add(sub.id)
        elif isinstance(sub, ast.Attribute):
            base = sub
            while isinstance(base, ast.Attribute):
                base = base.value
            if isinstance(base, ast.Name):
                names.add(base.id)
    return names


def _library_bindings(lib, tree):
    """Return the set of bound identifiers in `tree` that correspond to `lib`."""
    top = lib.split(".")[0]
    member = lib.split(".")[1] if "." in lib else None
    imports = _collect_imports(tree)
    bindings = set()
    for bound, spec in imports.items():
        if spec[0] == "module" and spec[1].split(".")[0] == top:
            bindings.add(bound)
        elif spec[0] == "from" and spec[1].split(".")[0] == top:
            if member is None or spec[2] == member or bound == member:
                bindings.add(bound)
    return bindings


def _check_function_uses_library(entry, located):
    """For each claimed function, determine which claimed libraries it DIRECTLY
    references (the library's bound name appears in the function body)."""
    libs = entry.get("librariesUsed", [])
    per_function = []
    any_link = False

    for ref in entry.get("functionNames", []):
        rel, _, func = ref.partition("::")
        if rel not in located or func not in located[rel][1]:
            per_function.append({"ref": ref, "libs_used": [], "uses_any": False,
                                 "note": "function not found"})
            continue
        node = located[rel][1][func]
        body_names = _names_in_node(node)
        tree = located[rel][0]

        used_here = [lib for lib in libs if _library_bindings(lib, tree) & body_names]
        if used_here:
            any_link = True
        per_function.append({"ref": ref, "libs_used": used_here,
                             "uses_any": bool(used_here), "note": ""})

    level1 = PRESENT if any_link else (ABSENT if libs and entry.get("functionNames") else PRESENT)
    return per_function, level1


def _combine(statuses):
    if not statuses:
        return PRESENT
    return min(statuses, key=lambda s: RANK.get(s, 1))


class StaticQualityAttributeValidator(IStaticQualityValidator):
    """
    Stage 3 – Static Quality Attribute (NFR trace) Validator:
    - Locates the NFR trace file inside the generated code dir
    - Verifies EXISTENCE only (no behavior): tactics resolve against the
      catalog, claimed files/functions exist and are non-trivial, and claimed
      libraries are imported and used
    - The weakest claim in an NFR entry sets that entry's verdict; the
      weakest entry verdict across the trace sets the overall pass/fail
    """

    def __init__(self, config: dict | None = None) -> None:
        config = config or {}
        validator_cfg = config.get("validator", {})
        self._nfr_trace_filename = validator_cfg.get("nfr_trace_filename", "nfr-trace.json")
        self._catalog_path = Path(validator_cfg.get("tactic_catalog_path", HERE / "tactic_catalog.json"))
        self._history_path = Path(validator_cfg.get("tactic_history_path", HERE / "outputs" / "tactic_lib_history.json"))
        self._report_dir = Path(config.get("output", {}).get("report_dir", "reports/"))

    def _load_known_tactics(self):
        try:
            cat = json.loads(self._catalog_path.read_text())["tactics"]
            return set(cat)
        except Exception:
            return None  # accept any tactic if catalog missing

    def _resolve(self, entry, known_tactics):
        tactics = _split_tactics(entry["tacticUsed"])
        if known_tactics is None:
            return OK, "catalog missing — tactics accepted", tactics
        unknown = [t for t in tactics if t not in known_tactics]
        if unknown:
            return OUT_OF_CATALOG, f"unknown tactic(s): {unknown}", tactics
        return OK, f"tactics resolved: {tactics}", tactics

    def _locate(self, entry, repo_root):
        missing_files = [rel for rel in entry["filesImplemented"] if not (repo_root / rel).is_file()]
        if missing_files:
            return ABSENT, f"missing file(s): {missing_files}", None

        located = {}
        for rel in entry["filesImplemented"]:
            tree, err = _parse_file(repo_root / rel)
            if err:
                return ABSENT, f"{rel}: {err}", None
            located[rel] = (tree, _function_defs(tree))
        return OK, "all files parsed", located

    def _verify(self, trace, repo_root, known_tactics):
        results = []
        for entry in trace["nfrTrace"]:
            r_status, r_ev, tactics = self._resolve(entry, known_tactics)
            if r_status != OK:
                results.append({"nfr": entry["nfr"], "status": r_status, "stage": "resolve",
                                "evidence": r_ev, "tactics": tactics,
                                "functions": [], "libraries": []})
                continue

            l_status, l_ev, located = self._locate(entry, repo_root)
            if l_status != OK:
                results.append({"nfr": entry["nfr"], "status": l_status, "stage": "locate",
                                "evidence": l_ev, "tactics": tactics,
                                "functions": [], "libraries": []})
                continue

            fn_details = _check_functions(entry, located)
            lib_details = _check_libraries(entry, located)
            fn_lib, level1 = _check_function_uses_library(entry, located)

            all_statuses = [st for _, st, _ in fn_details] + [st for _, st, _ in lib_details] + [level1]
            combined = _combine(all_statuses)

            fn_str = "; ".join(f"{ref.split('::')[-1]}={st}" for ref, st, _ in fn_details)
            lib_str = "; ".join(f"{lib}={st}" for lib, st, _ in lib_details)
            link_str = "; ".join(f"{i['ref'].split('::')[-1]}->{i['libs_used'] or 'none'}" for i in fn_lib)
            evidence = f"functions[{fn_str}] libraries[{lib_str}] fn-uses-lib[level1={level1}; {link_str}]"

            results.append({
                "nfr": entry["nfr"],
                "status": combined,
                "stage": "existence",
                "evidence": evidence,
                "tactics": tactics,
                "functions": [{"ref": r, "status": s, "detail": e} for r, s, e in fn_details],
                "libraries": [{"lib": l, "status": s, "detail": e} for l, s, e in lib_details],
                "function_library_usage": {"level1": level1, "per_function": fn_lib},
            })
        return results

    def _update_history(self, trace):
        """Accumulate tactic -> [all claimed libraries] across every run."""
        self._history_path.parent.mkdir(parents=True, exist_ok=True)
        history = {}
        if self._history_path.is_file():
            try:
                history = json.loads(self._history_path.read_text(encoding="utf-8"))
            except Exception:
                history = {}
        for entry in trace["nfrTrace"]:
            tactics = _split_tactics(entry.get("tacticUsed", ""))
            libs = entry.get("librariesUsed", [])
            for tactic in tactics:
                existing = set(history.get(tactic, []))
                existing.update(libs)
                history[tactic] = sorted(existing)
        self._history_path.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")

    def _write_json_report(self, trace_path, repo_root, results, counts) -> str:
        self._report_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self._report_dir / f"static_qa_report_{timestamp}.json"
        payload = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "trace_file": str(trace_path),
            "repo_root": str(repo_root),
            "tally": counts,
            "results": results,
        }
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return str(path)

    def validate(self, generation_result: GenerationResult) -> ValidationResult:
        repo_root = Path(generation_result.code)
        trace_path = repo_root / self._nfr_trace_filename

        if not trace_path.is_file():
            return ValidationResult(
                stage="static_qa",
                status=Status.FAIL,
                message=f"NFR trace file not found: {trace_path}",
                details={"error": "FileNotFoundError"},
            )

        try:
            trace = json.loads(trace_path.read_text(encoding="utf-8"))
        except Exception as e:
            return ValidationResult(
                stage="static_qa",
                status=Status.FAIL,
                message=f"Failed to read/parse NFR trace: {e}",
                details={"error": str(e)},
            )

        known_tactics = self._load_known_tactics()
        results = self._verify(trace, repo_root, known_tactics)

        counts: dict[str, int] = {}
        for r in results:
            counts[r["status"]] = counts.get(r["status"], 0) + 1

        statuses = set(counts)
        if ABSENT in statuses or OUT_OF_CATALOG in statuses:
            status = Status.FAIL
            message = f"NFR trace has absent/out-of-catalog claim(s): {counts}"
        elif WEAK in statuses:
            status = Status.FAIL
            message = f"NFR trace has weak claim(s) needing review: {counts}"
        else:
            status = Status.PASS
            message = f"All {len(results)} NFR entries verified present: {counts}"

        report_path = self._write_json_report(trace_path, repo_root, results, counts)
        self._update_history(trace)

        return ValidationResult(
            stage="static_qa",
            status=status,
            message=message,
            details={"tally": counts, "report_path": report_path},
        )
