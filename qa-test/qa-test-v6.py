"""
NFR trace verifier v5 — EXISTENCE checking (no behavior).

For each NFR entry, verify the trace's claims actually exist in the claimed files:
  1. RESOLVE  — is every claimed tactic a known tactic (catalog membership)?
  2. LOCATE   — do the claimed files exist, and do the claimed functions
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

A JSON report is written to ./outputs/<trace-stem>.report.json next to this script.
"""

#python qa-test-v6.py "C:\Swinburne Class\SwinLab\llmgenmt\llmagent4code\qa-test\sdk-0\code_workspace\nfr-trace.json"

import ast
import json
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).parent
CATALOG_PATH = HERE / "tactic_catalog.json"

# --- verdict labels ---
OK = "RESOLVED_OK"
ABSENT = "ABSENT"
WEAK = "WEAK"
PRESENT = "PRESENT"
OUT_OF_CATALOG = "OUT_OF_CATALOG"

# rank for combining: weakest wins
RANK = {ABSENT: 0, WEAK: 1, PRESENT: 2}


def log(msg="", indent=0):
    print(f"{'    ' * indent}{msg}")


# ---------------------------------------------------------------------------
# catalog (tactic membership only — no detectors in v5)
# ---------------------------------------------------------------------------
def load_known_tactics():
    try:
        cat = json.loads(CATALOG_PATH.read_text())["tactics"]
        return set(cat)
    except Exception:
        return None  # accept any tactic if catalog missing


def leaf_tactic(tactic_str):
    return tactic_str.split(">")[-1].strip()


def split_tactics(tactic_field):
    return [leaf_tactic(t) for t in tactic_field.split(";") if t.strip()]


# ---------------------------------------------------------------------------
# parsing helpers
# ---------------------------------------------------------------------------
def parse_file(path):
    try:
        return ast.parse(Path(path).read_text(encoding="utf-8")), None
    except (SyntaxError, UnicodeDecodeError) as e:
        return None, f"parse error: {e}"


def function_defs(tree):
    out = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.setdefault(node.name, node)
    return out


# ---------------------------------------------------------------------------
# FUNCTION non-triviality (stub detection)
# ---------------------------------------------------------------------------
def is_stub(func_node):
    """A function is a stub if its body is only: pass / ... / a docstring /
    raise NotImplementedError / a bare `return` or `return None`."""
    body = list(func_node.body)
    # strip a leading docstring
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


def check_functions(entry, located):
    """Return a list of (ref, status, detail) per claimed function."""
    results = []
    for ref in entry.get("functionNames", []):
        rel, _, func = ref.partition("::")
        if rel not in located or func not in located[rel][1]:
            results.append((ref, ABSENT, "function not found"))
            continue
        node = located[rel][1][func]
        if is_stub(node):
            results.append((ref, WEAK, "empty stub (pass/…/NotImplementedError/docstring only)"))
        else:
            results.append((ref, PRESENT, "non-trivial body"))
    return results


# ---------------------------------------------------------------------------
# LIBRARY imported-and-used
# ---------------------------------------------------------------------------
def collect_imports(tree):
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


def name_used_outside_imports(tree, bound_name):
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


def attribute_path_used(tree, module_name, attr):
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == attr:
            base = node.value
            if isinstance(base, ast.Name) and base.id == module_name:
                return True
    return False


def check_library(lib, located):
    top = lib.split(".")[0]
    member = lib.split(".")[1] if "." in lib else None
    imported_anywhere = False
    used = False
    for rel in located:
        tree = located[rel][0]
        imports = collect_imports(tree)
        # ALL bindings from this package, not just the last
        bounds = [b for b, spec in imports.items()
                  if spec[1].split(".")[0] == top]
        if not bounds:
            continue
        imported_anywhere = True
        if member:
            for b, spec in imports.items():
                if spec[0] == "from" and spec[1].split(".")[0] == top and spec[2] == member \
                        and name_used_outside_imports(tree, b):
                    used = True
                if spec[0] == "module" and spec[1].split(".")[0] == top \
                        and attribute_path_used(tree, b, member):
                    used = True
        else:
            if any(name_used_outside_imports(tree, b) for b in bounds):
                used = True
    if not imported_anywhere:
        return ABSENT, f"'{lib}' not imported in any claimed file"
    if not used:
        return WEAK, f"'{lib}' imported but not used (dead import)"
    return PRESENT, f"'{lib}' imported and used"


def check_libraries(entry, located):
    results = []
    for lib in entry.get("librariesUsed", []):
        status, ev = check_library(lib, located)
        results.append((lib, status, ev))
    return results


# ---------------------------------------------------------------------------
# FUNCTION-USES-LIBRARY (direct reference only)
# ---------------------------------------------------------------------------
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
    """Return the set of bound identifiers in `tree` that correspond to `lib`.
    Handles 'pkg', 'pkg.Member', aliases, and from-imports.
    e.g. import asyncio           -> {'asyncio'}
         from tenacity import retry -> {'retry'}
         from asyncio import Queue  -> {'Queue'}   (for lib 'asyncio.Queue')
         import numpy as np         -> {'np'}
    """
    top = lib.split(".")[0]
    member = lib.split(".")[1] if "." in lib else None
    imports = collect_imports(tree)
    bindings = set()
    for bound, spec in imports.items():
        if spec[0] == "module" and spec[1].split(".")[0] == top:
            bindings.add(bound)
        elif spec[0] == "from" and spec[1].split(".")[0] == top:
            # from pkg import X  -> X is a valid binding for the library;
            # if lib names a member, prefer that member's binding
            if member is None or spec[2] == member or bound == member:
                bindings.add(bound)
    return bindings


def check_function_uses_library(entry, located):
    """For each claimed function, determine which claimed libraries it DIRECTLY
    references (the library's bound name appears in the function body).

    Returns:
      per_function: list of {ref, libs_used:[...], uses_any:bool}
      level1: 'PRESENT' if any claimed function uses any claimed library, else 'ABSENT'
    """
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

        used_here = []
        for lib in libs:
            bindings = _library_bindings(lib, tree)
            if bindings & body_names:
                used_here.append(lib)
        if used_here:
            any_link = True
        per_function.append({"ref": ref, "libs_used": used_here,
                             "uses_any": bool(used_here), "note": ""})

    level1 = PRESENT if any_link else (ABSENT if libs and entry.get("functionNames") else PRESENT)
    return per_function, level1



# ---------------------------------------------------------------------------
# stages
# ---------------------------------------------------------------------------
def resolve(entry, known_tactics):
    tactics = split_tactics(entry["tacticUsed"])
    log(f"[resolve] leaf tactics: {tactics}", 2)
    if known_tactics is None:
        return OK, "catalog missing — tactics accepted", tactics
    unknown = [t for t in tactics if t not in known_tactics]
    for t in tactics:
        log(f"[resolve]   - {t!r} -> {'known' if t not in unknown else 'UNKNOWN'}", 2)
    if unknown:
        return OUT_OF_CATALOG, f"unknown tactic(s): {unknown}", tactics
    return OK, f"tactics resolved: {tactics}", tactics


def locate(entry, repo_root):
    missing_files = []
    for rel in entry["filesImplemented"]:
        full = repo_root / rel
        exists = full.is_file()
        log(f"[locate]   {'OK ' if exists else 'MISS'} file: {rel}  -> {full}", 2)
        if not exists:
            missing_files.append(rel)
    if missing_files:
        return ABSENT, f"missing file(s): {missing_files}", None

    located = {}
    for rel in entry["filesImplemented"]:
        tree, err = parse_file(repo_root / rel)
        if err:
            return ABSENT, f"{rel}: {err}", None
        located[rel] = (tree, function_defs(tree))
        log(f"[locate]   parsed {rel}: {sorted(located[rel][1])}", 2)
    return OK, "all files parsed", located


# ---------------------------------------------------------------------------
# driver
# ---------------------------------------------------------------------------
def combine(statuses):
    if not statuses:
        return PRESENT
    return min(statuses, key=lambda s: RANK.get(s, 1))


def verify(trace, repo_root, known_tactics):
    results = []
    total = len(trace["nfrTrace"])
    for i, entry in enumerate(trace["nfrTrace"], 1):
        log()
        log(f"=== [{i}/{total}] {entry['nfr']} ===", 1)

        r_status, r_ev, tactics = resolve(entry, known_tactics)
        log(f"[resolve] -> {r_status}: {r_ev}", 2)
        if r_status != OK:
            results.append({"nfr": entry["nfr"], "status": r_status, "stage": "resolve",
                            "evidence": r_ev, "tactics": tactics,
                            "functions": [], "libraries": []})
            continue

        l_status, l_ev, located = locate(entry, repo_root)
        log(f"[locate] -> {l_status}: {l_ev}", 2)
        if l_status != OK:
            results.append({"nfr": entry["nfr"], "status": l_status, "stage": "locate",
                            "evidence": l_ev, "tactics": tactics,
                            "functions": [], "libraries": []})
            continue

        # FUNCTIONS
        fn_details = check_functions(entry, located)
        for ref, st, ev in fn_details:
            log(f"[functions] {st:<8} {ref} — {ev}", 2)

        # LIBRARIES
        lib_details = check_libraries(entry, located)
        for lib, st, ev in lib_details:
            log(f"[libraries] {st:<8} {ev}", 2)

        # FUNCTION-USES-LIBRARY (direct reference)
        fn_lib, level1 = check_function_uses_library(entry, located)
        for item in fn_lib:
            fn_name = item["ref"].split("::")[-1]
            if item["uses_any"]:
                log(f"[fn-uses-lib] {fn_name} -> uses {item['libs_used']}", 2)
            else:
                extra = f" ({item['note']})" if item["note"] else " (uses no claimed library — informational)"
                log(f"[fn-uses-lib] {fn_name} -> none{extra}", 2)
        log(f"[fn-uses-lib] level1 (any function uses any lib) -> {level1}", 2)

        # combine: functions + libraries + level1 link (per-function level2 is informational)
        all_statuses = [st for _, st, _ in fn_details] + [st for _, st, _ in lib_details] + [level1]
        combined = combine(all_statuses)
        log(f"[combine] -> {combined}", 2)

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
            "function_library_usage": {
                "level1": level1,
                "per_function": fn_lib,
            },
        })
    return results


def aggregate_exit_code(results):
    statuses = {r["status"] for r in results}
    if ABSENT in statuses or OUT_OF_CATALOG in statuses:
        return 1
    if WEAK in statuses:
        return 2
    return 0


def write_report(out_dir, trace_path, repo_root, results, counts, code):
    out_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "trace_file": str(trace_path),
        "repo_root": str(repo_root),
        "exit_code": code,
        "tally": counts,
        "results": results,
    }
    out_path = out_dir / f"{trace_path.stem}.report.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_path


def main():
    if len(sys.argv) != 2:
        print("usage: python qa-test-v5.py <path-to-nfr-trace.json>")
        sys.exit(64)
    trace_path = Path(sys.argv[1]).expanduser().resolve()
    if not trace_path.is_file():
        print(f"trace not found: {trace_path}")
        sys.exit(64)
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    repo_root = trace_path.parent
    known_tactics = load_known_tactics()

    log("=" * 64)
    log("NFR TRACE VERIFIER v5 — EXISTENCE (files, functions, libraries)")
    log("=" * 64)
    log(f"trace file : {trace_path}")
    log(f"repo root  : {repo_root}")
    log(f"tactics    : {'catalog loaded' if known_tactics else 'no catalog (accept all)'}")

    results = verify(trace, repo_root, known_tactics)

    log()
    log("=" * 64)
    log("SUMMARY")
    log("=" * 64)
    for r in results:
        print(f"[{r['status']:<14}] {r['nfr']:<42} ({r['stage']})")
        print(f"                 {r['evidence']}")

    counts = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    log()
    log(f"tally: {counts}")

    code = aggregate_exit_code(results)
    print(f"\noverall exit code: {code}  (0=all present, 1=absent/out-of-catalog, 2=weak needs review)")

    out_path = write_report(HERE / "outputs", trace_path, repo_root, results, counts, code)
    print(f"report written: {out_path}")

    sys.exit(code)


if __name__ == "__main__":
    main()