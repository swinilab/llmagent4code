"""
NFR trace verifier — steps 1 (resolve) + 2 (locate) + 3 (detect).

Given a trace.json (agent claims) and a repo root (real code), for each NFR entry:
  1. RESOLVE  — is every claimed tactic a known tactic (in the catalog)?
  2. LOCATE   — do the claimed files exist, and do the claimed functions
                exist inside them?
  3. DETECT   — does each claimed function actually IMPLEMENT the tactic?
                (anchor present + discriminator confirms it is real)

Verdicts per stage: RESOLVED_OK / OUT_OF_CATALOG (step 1),
ABSENT (step 2 missing file/func), and PRESENT / WEAK / ABSENT (step 3).
Output: per-NFR verdict + exit code.
"""

#python qa-test-v4.py "C:\Swinburne Class\SwinLab\llmgenmt\llmagent4code\qa-test\sdk-0\code_workspace\nfr-trace.json"

#

import ast
import json
import sys
import importlib
from pathlib import Path

HERE = Path(__file__).parent
CATALOG_PATH = HERE / "tactic_catalog.json"

# --- verdict labels ---
OK = "RESOLVED_OK"
ABSENT = "ABSENT"
WEAK = "WEAK"
PRESENT = "PRESENT"
MISLOCATED = "MISLOCATED"
OUT_OF_CATALOG = "OUT_OF_CATALOG"


def log(msg="", indent=0):
    print(f"{'    ' * indent}{msg}")


# ---------------------------------------------------------------------------
# catalog + detector loading
# ---------------------------------------------------------------------------
def load_catalog():
    return json.loads(CATALOG_PATH.read_text())["tactics"]


def load_detector(rel_path):
    """Import a detector as a package member (so 'from .astutils import ...'
    works) and return its detect(). rel_path like 'detectors/detect_x.py'."""
    path = (HERE / rel_path)
    if not path.is_file():
        return None, f"detector file not found: {rel_path}"
    # build dotted module name: detectors/detect_x.py -> detectors.detect_x
    dotted = rel_path.replace("/", ".").replace("\\", ".")
    if dotted.endswith(".py"):
        dotted = dotted[:-3]
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    try:
        mod = importlib.import_module(dotted)
    except Exception as e:
        return None, f"detector import error ({rel_path}): {e}"
    if not hasattr(mod, "detect"):
        return None, f"detector {rel_path} has no detect()"
    return mod.detect, None


def build_detector_map(catalog):
    detectors, load_errors = {}, {}
    for tactic, spec in catalog.items():
        fn, err = load_detector(spec["verification_implementation"])
        if err:
            load_errors[tactic] = err
        else:
            detectors[tactic] = fn
    return detectors, load_errors


# ---------------------------------------------------------------------------
# tactic string parsing
# ---------------------------------------------------------------------------
def leaf_tactic(tactic_str):
    """'Performance > Manage Resources > Bound Queue Sizes' -> 'Bound Queue Sizes'."""
    return tactic_str.split(">")[-1].strip()


def split_tactics(tactic_field):
    """NFR 2.2 packs two tactics separated by ';'. Return list of leaf names."""
    return [leaf_tactic(t) for t in tactic_field.split(";") if t.strip()]


# ---------------------------------------------------------------------------
# step 2 helpers — returns located AST nodes for step 3
# ---------------------------------------------------------------------------
def parse_file(path):
    try:
        return ast.parse(Path(path).read_text()), None
    except (SyntaxError, UnicodeDecodeError) as e:
        return None, f"parse error: {e}"


def function_defs(tree):
    out = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.setdefault(node.name, node)
    return out


# ---------------------------------------------------------------------------
# stages
# ---------------------------------------------------------------------------
def resolve(entry, catalog):
    tactics = split_tactics(entry["tacticUsed"])
    unknown = [t for t in tactics if t not in catalog]
    log(f"[resolve] leaf tactics: {tactics}", 2)
    for t in tactics:
        log(f"[resolve]   - {t!r} -> {'known' if t not in unknown else 'UNKNOWN'}", 2)
    if unknown:
        return OUT_OF_CATALOG, f"unknown tactic(s): {unknown}", tactics
    return OK, f"tactics resolved: {tactics}", tactics


def locate(entry, repo_root):
    """Return (status, evidence, located) where located maps file->(tree, {func:node})."""
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

    missing_funcs = []
    for ref in entry.get("functionNames", []):
        rel, _, func = ref.partition("::")
        if rel not in located:
            missing_funcs.append(f"{ref} (file not in filesImplemented)")
        elif func not in located[rel][1]:
            missing_funcs.append(ref)
        else:
            log(f"[locate]   OK   func: {ref}", 2)
    if missing_funcs:
        return ABSENT, f"missing function(s): {missing_funcs}", None

    return OK, "all files and functions located", located


def detect(entry, tactics, located, detectors, repo_root):
    """Run the detector for each claimed tactic. Combine multi-tactic entries by
    taking the WEAKEST verdict.  With multi-file entries, the detector receives
    ALL claimed function nodes (across every claimed file) plus ALL claimed
    trees, so it can search the full declared surface — not just one file."""
    order = {ABSENT: 0, MISLOCATED: 1, WEAK: 2, PRESENT: 3}

    # gather ALL claimed function nodes across every claimed file (once per entry)
    func_nodes = []
    for ref in entry.get("functionNames", []):
        rel, _, func = ref.partition("::")
        if rel in located and func in located[rel][1]:
            func_nodes.append(located[rel][1][func])
    # all trees for the entry's claimed files (for file-scope fallback searches)
    trees = [located[rel][0] for rel in located]

    log(f"[detect] inspecting functions: {[fn.name for fn in func_nodes]}", 2)
    log(f"[detect] claimed files (trees): {list(located.keys())}", 2)
    if not func_nodes:
        log(f"[detect]   WARNING: no claimed functions resolved to nodes", 2)

    per = []
    for tactic in tactics:
        det = detectors.get(tactic)
        if det is None:
            per.append((tactic, WEAK, "no detector loaded (skipped)"))
            log(f"[detect]   {tactic}: WEAK — no detector loaded (skipped)", 2)
            continue
        try:
            status, ev = det(func_nodes, trees, "", entry)
        except Exception as e:
            status, ev = WEAK, f"detector raised: {e}"
        per.append((tactic, status, ev))
        log(f"[detect]   {tactic}: {status} — {ev}", 2)

    # combine: weakest verdict wins
    worst = min(per, key=lambda p: order.get(p[1], 1))
    combined = worst[1]
    detail = "; ".join(f"{t}={s}" for t, s, _ in per)
    evidence = " | ".join(f"{t}: {e}" for t, s, e in per)
    log(f"[detect] combined -> {combined}  ({detail})", 2)
    return combined, f"[{detail}] {evidence}"


# ---------------------------------------------------------------------------
# driver
# ---------------------------------------------------------------------------
def verify(trace, repo_root, catalog, detectors):
    results = []
    total = len(trace["nfrTrace"])
    for i, entry in enumerate(trace["nfrTrace"], 1):
        log()
        log(f"=== [{i}/{total}] {entry['nfr']} ===", 1)

        r_status, r_ev, tactics = resolve(entry, catalog)
        log(f"[resolve] -> {r_status}: {r_ev}", 2)
        if r_status != OK:
            results.append({"nfr": entry["nfr"], "status": r_status, "stage": "resolve", "evidence": r_ev})
            continue

        l_status, l_ev, located = locate(entry, repo_root)
        log(f"[locate] -> {l_status}: {l_ev}", 2)
        if l_status != OK:
            results.append({"nfr": entry["nfr"], "status": l_status, "stage": "locate", "evidence": l_ev})
            continue

        d_status, d_ev = detect(entry, tactics, located, detectors, repo_root)
        log(f"[detect] -> {d_status}", 2)
        results.append({"nfr": entry["nfr"], "status": d_status, "stage": "detect", "evidence": d_ev})
    return results


def aggregate_exit_code(results):
    statuses = {r["status"] for r in results}
    if ABSENT in statuses or OUT_OF_CATALOG in statuses:
        return 1
    if WEAK in statuses or MISLOCATED in statuses:
        return 2
    return 0


def main():
    if len(sys.argv) != 2:
        print("usage: python qa-test-v4.py <path-to-nfr-trace.json>")
        sys.exit(64)
    trace_path = Path(sys.argv[1]).expanduser().resolve()
    if not trace_path.is_file():
        print(f"trace not found: {trace_path}")
        sys.exit(64)
    trace = json.loads(trace_path.read_text())
    repo_root = trace_path.parent

    catalog = load_catalog()
    detectors, load_errors = build_detector_map(catalog)

    log("=" * 64)
    log("NFR TRACE VERIFIER — steps 1 (resolve) + 2 (locate) + 3 (detect)")
    log("=" * 64)
    log(f"trace file : {trace_path}")
    log(f"repo root  : {repo_root}")
    log(f"catalog    : {len(catalog)} tactics, {len(detectors)} detectors loaded")
    for t, e in load_errors.items():
        log(f"  ! detector load error [{t}]: {e}")

    results = verify(trace, repo_root, catalog, detectors)

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
    sys.exit(code)


if __name__ == "__main__":
    main()