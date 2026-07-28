"""
NFR trace verifier — steps 1 (resolve) + 2 (locate).

Given a trace.json (agent claims) and a repo root (real code), for each NFR entry:
  1. RESOLVE  — is every claimed tactic a known tactic?
  2. LOCATE   — do the claimed files exist, and do the claimed functions
                exist inside them?

No detectors yet (that's step 3). This only proves the trace points at real
files and real functions. Output: per-NFR verdict + exit code.
"""

#python qa-test-v3.py "C:\Swinburne Class\SwinLab\llmgenmt\llmagent4code\method_pipeline_v2\generated\sdk_chatdev_20260725155724_20260725155724\code_workspace\nfr-trace.json"

import ast
import json
import sys
from pathlib import Path

# --- step 1 catalog: known tactics (membership only, detectors come in step 3) ---
KNOWN_TACTICS = {
    "Maintain Multiple Copies of Computations",
    "Introduce Concurrency",
    "Bound Queue Sizes",
    "Degradation",
    "Ping/Echo",
    "Retry",
    "State Resynchronization",
}

# --- verdict labels ---
OK = "RESOLVED_OK"
ABSENT = "ABSENT"
OUT_OF_CATALOG = "OUT_OF_CATALOG"


def log(msg="", indent=0):
    """Simple indented logger for readable step-by-step output."""
    print(f"{'    ' * indent}{msg}")


def leaf_tactic(tactic_str):
    """'Performance > Manage Resources > Bound Queue Sizes' -> 'Bound Queue Sizes'."""
    return tactic_str.split(">")[-1].strip()


def split_tactics(tactic_field):
    """NFR 2.2 packs two tactics separated by ';'. Return a list of leaf names."""
    return [leaf_tactic(t) for t in tactic_field.split(";") if t.strip()]


def function_names_in_file(path):
    """Parse a file's AST once, return the set of all def/async-def names (any nesting)."""
    try:
        tree = ast.parse(Path(path).read_text())
    except (SyntaxError, UnicodeDecodeError) as e:
        return None, f"parse error: {e}"
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.add(node.name)
    return names, None


def resolve(entry):
    """Step 1: every claimed tactic must be in the catalog."""
    tactics = split_tactics(entry["tacticUsed"])
    log(f"[resolve] raw tacticUsed: {entry['tacticUsed']!r}", 2)
    log(f"[resolve] parsed leaf tactics: {tactics}", 2)
    unknown = [t for t in tactics if t not in KNOWN_TACTICS]
    for t in tactics:
        mark = "known" if t not in unknown else "UNKNOWN"
        log(f"[resolve]   - {t!r} -> {mark}", 2)
    if unknown:
        return OUT_OF_CATALOG, f"unknown tactic(s): {unknown}"
    return OK, f"tactics resolved: {tactics}"


def locate(entry, repo_root):
    """Step 2: files exist on disk, functions exist inside them."""
    # 2a: file existence
    log(f"[locate] checking {len(entry['filesImplemented'])} claimed file(s)", 2)
    missing_files = []
    for rel in entry["filesImplemented"]:
        full = repo_root / rel
        exists = full.is_file()
        log(f"[locate]   {'OK ' if exists else 'MISS'} file: {rel}", 2)
        log(f"[locate]        -> {full}", 2)
        if not exists:
            missing_files.append(rel)
    if missing_files:
        return ABSENT, f"missing file(s): {missing_files}"

    # cache: parse each referenced file once
    file_funcs = {}
    for rel in entry["filesImplemented"]:
        names, err = function_names_in_file(repo_root / rel)
        if err:
            log(f"[locate]   PARSE-FAIL {rel}: {err}", 2)
            return ABSENT, f"{rel}: {err}"
        file_funcs[rel] = names
        log(f"[locate]   parsed {rel}: {sorted(names)}", 2)

    # 2b: function existence  ('path::func')
    log(f"[locate] checking {len(entry.get('functionNames', []))} claimed function(s)", 2)
    missing_funcs = []
    for ref in entry.get("functionNames", []):
        rel, _, func = ref.partition("::")
        if rel not in file_funcs:
            log(f"[locate]   MISS func: {ref}  (file not in filesImplemented)", 2)
            missing_funcs.append(f"{ref} (file not in filesImplemented)")
        elif func not in file_funcs[rel]:
            log(f"[locate]   MISS func: {ref}", 2)
            missing_funcs.append(ref)
        else:
            log(f"[locate]   OK   func: {ref}", 2)
    if missing_funcs:
        return ABSENT, f"missing function(s): {missing_funcs}"

    return OK, "all files and functions located"


def verify(trace, repo_root):
    results = []
    total = len(trace["nfrTrace"])
    for i, entry in enumerate(trace["nfrTrace"], 1):
        log()
        log(f"=== [{i}/{total}] {entry['nfr']} ===", 1)
        r_status, r_ev = resolve(entry)
        log(f"[resolve] -> {r_status}: {r_ev}", 2)
        if r_status != OK:
            log(f"[skip] resolve failed, not locating", 2)
            results.append({"nfr": entry["nfr"], "status": r_status,
                            "stage": "resolve", "evidence": r_ev})
            continue
        l_status, l_ev = locate(entry, repo_root)
        log(f"[locate] -> {l_status}: {l_ev}", 2)
        results.append({"nfr": entry["nfr"], "status": l_status,
                        "stage": "locate", "evidence": l_ev})
    return results


def aggregate_exit_code(results):
    if any(r["status"] == ABSENT for r in results):
        return 1
    if any(r["status"] == OUT_OF_CATALOG for r in results):
        return 2
    return 0


def main():
    if len(sys.argv) != 2:
        print("usage: python verify.py <path-to-nfr-trace.json>")
        sys.exit(64)
    trace_path = Path(sys.argv[1]).expanduser().resolve()
    if not trace_path.is_file():
        print(f"trace not found: {trace_path}")
        sys.exit(64)
    trace = json.loads(trace_path.read_text())
    repo_root = trace_path.parent

    log("=" * 60)
    log("NFR TRACE VERIFIER — steps 1 (resolve) + 2 (locate)")
    log("=" * 60)
    log(f"trace file : {trace_path}")
    log(f"repo root  : {repo_root}")
    log(f"entries    : {len(trace['nfrTrace'])}")

    results = verify(trace, repo_root)

    log()
    log("=" * 60)
    log("SUMMARY")
    log("=" * 60)
    for r in results:
        print(f"[{r['status']:<15}] {r['nfr']:<40} ({r['stage']}) — {r['evidence']}")

    counts = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    log()
    log(f"tally: {counts}")

    code = aggregate_exit_code(results)
    print(f"\noverall exit code: {code}  (0=pass, 1=absent, 2=out-of-catalog)")
    sys.exit(code)


if __name__ == "__main__":
    main()