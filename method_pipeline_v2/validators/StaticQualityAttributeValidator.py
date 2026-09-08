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
    app_run_dir,
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
    """Extract leaf tactic name from hierarchical paths like:
    'QA Performance/Manage Resources/Limit Event Response' or
    'QA Performance > Manage Resources > Limit Event Response' -> 'Limit Event Response'
    """
    clean = tactic_str.replace(">", "/")
    return clean.split("/")[-1].strip()


def _split_tactics(tactic_field):
    return [_leaf_tactic(t) for t in tactic_field.split(";") if t.strip()]


def _parse_file(path):
    try:
        return ast.parse(Path(path).read_text(encoding="utf-8-sig")), None
    except (SyntaxError, UnicodeDecodeError) as e:
        return None, f"parse error: {e}"


def _function_defs(tree):
    """name -> node for every function/method. Methods are registered under
    both their bare name ('place_order') and their qualified name
    ('OrderService.place_order') so traces can use either form."""
    out = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.setdefault(node.name, node)
    for cls in ast.walk(tree):
        if isinstance(cls, ast.ClassDef):
            for item in cls.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    out.setdefault(f"{cls.name}.{item.name}", item)
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

def _call_base_name(value):
    """If `value` is a call like `asyncio.Queue(...)` or `Queue(...)`, return
    the base identifier ('asyncio' or 'Queue'); else None."""
    if not isinstance(value, ast.Call):
        return None
    func = value.func
    if isinstance(func, ast.Name):
        return func.id
    while isinstance(func, ast.Attribute):
        func = func.value
    return func.id if isinstance(func, ast.Name) else None

def _init_param_library_map(classdef, libs, tree):
    """param name -> claimed lib, read off the type annotations of __init__.

    Constructor injection is how the generated apps normally reach a library:
    `def __init__(self, redis: Redis)` followed by `self._redis = redis`. The
    assignment carries no library name at all - only the annotation does - so
    without this the whole class looks library-free and every one of its methods
    is scored 0.5 for a claim it does honour. That penalises dependency
    injection relative to constructing the client inline, which is a coding
    style, not a difference in conformance.
    """
    param_map = {}
    for item in classdef.body:
        if not (isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                and item.name == "__init__"):
            continue
        args = item.args
        for arg in (list(getattr(args, "posonlyargs", [])) + list(args.args)
                    + list(args.kwonlyargs)):
            if arg.annotation is None:
                continue
            annotated = _names_in_node(arg.annotation)
            for lib in libs:
                if annotated & _library_bindings(lib, tree):
                    param_map[arg.arg] = lib
                    break
    return param_map


def _class_attr_library_map(classdef, libs, tree):
    """For one ClassDef, map self.<attr> -> claimed lib, from assignments like
    `self._queue = asyncio.Queue(...)` (Assign and AnnAssign), and from
    constructor injection (`self._redis = redis` where `redis: Redis`)."""
    attr_map = {}
    param_libs = _init_param_library_map(classdef, libs, tree)
    for node in ast.walk(classdef):
        target = value = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target, value = node.targets[0], node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            target, value = node.target, node.value
        if not (isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name) and target.value.id == "self"):
            continue
        base = _call_base_name(value)
        if base is None:
            # `self._redis = redis` - no call to inspect; the library is named
            # only by the constructor parameter's annotation.
            if isinstance(value, ast.Name) and value.id in param_libs:
                attr_map[target.attr] = param_libs[value.id]
            continue
        for lib in libs:
            if base in _library_bindings(lib, tree):
                attr_map[target.attr] = lib
                break
        else:
            # `self._session = session_factory()` where the factory itself was
            # injected: fall back to the parameter annotation.
            if base in param_libs:
                attr_map[target.attr] = param_libs[base]
    return attr_map


def _self_attrs_used(func_node):
    """Set of attr names accessed via self.<attr> inside the function."""
    attrs = set()
    for sub in ast.walk(func_node):
        if isinstance(sub, ast.Attribute) and isinstance(sub.value, ast.Name) \
                and sub.value.id == "self":
            attrs.add(sub.attr)
    return attrs


def _method_class_index(tree):
    """method name -> its enclosing ClassDef (first match wins).

    Keyed under both the bare name ('get') and the qualified name
    ('EntityCache.get'), matching `_function_defs`. Traces address methods in
    the qualified form, so a bare-name-only index made every qualified lookup
    miss and silently disabled the `self.<attr>` credit below it.
    """
    index = {}
    for cls in ast.walk(tree):
        if isinstance(cls, ast.ClassDef):
            for item in cls.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    index.setdefault(item.name, cls)
                    index.setdefault(f"{cls.name}.{item.name}", cls)
    return index


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
    """For each claimed function, determine which claimed libraries it references —
    either directly (the library's bound name appears in the body) or via a
    self.<attr> whose class-scope assignment resolves to a claimed library."""
    libs = entry.get("librariesUsed", [])
    per_function = []
    any_link = False

    for ref in entry.get("functionNames", []):
        rel, _, func = ref.partition("::")
        if rel not in located or func not in located[rel][1]:
            per_function.append({"ref": ref, "libs_used": [], "uses_any": False,
                                 "lib_claimed": bool(libs),
                                 "note": "function not found"})
            continue
        node = located[rel][1][func]
        body_names = _names_in_node(node)
        tree = located[rel][0]

        used_here = [lib for lib in libs if _library_bindings(lib, tree) & body_names]

        # Tier 1: credit self.<attr> whose class-scope assignment resolves to a lib
        class_index = _method_class_index(tree)
        if func in class_index:
            attr_map = _class_attr_library_map(class_index[func], libs, tree)
            for attr in _self_attrs_used(node):
                lib = attr_map.get(attr)
                if lib and lib not in used_here:
                    used_here.append(lib)

        if used_here:
            any_link = True
        per_function.append({"ref": ref, "libs_used": used_here,
                             "uses_any": bool(used_here),
                             "lib_claimed": bool(libs), "note": ""})

    level1 = PRESENT if any_link else (ABSENT if libs and entry.get("functionNames") else PRESENT)
    return per_function, level1


def _combine(statuses):
    if not statuses:
        return PRESENT
    return min(statuses, key=lambda s: RANK.get(s, 1))


# ─────────────────────────────────────────────────────────────────────────────
#  Scoring Engine (Mapped to plan.md Part 3: validate qa: static)
#
#  plan.md specification. plan.md calls these score1 / score2 / score3; the code
#  names each after what it scores, and the mapping is one-to-one:
#    3. validate qa: static
#       . ind-score: qa/ tactic @duc @hai
#         . score1 -> score_func(tactic, function)
#           . nfr-trace-> absent (0)/present (1)
#           [] . check lib code template: from (doc) -- code gen: similarity score 
#         . score2 -> score_tactic(tactic, function-in-trace) = % sum(score_func)/num-functions
#         . score3 -> score_qa(qa, tacticset) = avg(score_tactic-by-qa)
#
#  1. score_func(tactic, function)  - three levels, not binary:
#     - 1.0  PRESENT (non-trivial body) AND the function actually references a
#            library the trace claims for this NFR - the claim is corroborated
#            inside the function that makes it.
#     - 0.5  PRESENT but no claimed library is referenced anywhere in the body:
#            code exists, the library claim is unsupported at this call site.
#     - 0.0  WEAK (empty stub: pass / ... / NotImplementedError / docstring only /
#            return None) or ABSENT (function or file not found).
#     An entry that claims no library at all has nothing to corroborate, so its
#     functions are judged on the body alone and stay at 1.0 rather than being
#     docked for a claim they never made.
#     Rationale: the binary form saturated - 100/101 functions across the four
#     generated apps scored 1.0, so score_tactic/score_qa could not separate any
#     two apps.
#
#  2. score_tactic(tactic, function-in-trace):
#     - Percentage / ratio of valid functions implementing the tactic:
#       score_tactic(t) = sum(score_func(t, f) for f in functions_of(t)) / len(functions_of(t))
#     - If no functions are claimed for this tactic, score_tactic(t) = 0.0.
#
#  3. score_qa(qa, tacticset):
#     - Arithmetic mean of score_tactic across all tactics under that Quality Attribute:
#       score_qa(qa) = sum(score_tactic(t) for t in tactics_of(qa)) / len(tactics_of(qa))
#     - QA categorization is mapped strictly by NFR ID prefix:
#       "1.x" -> "performance"
#       "2.x" -> "availability"
#       other -> "other"
# ─────────────────────────────────────────────────────────────────────────────

def score_func(status: str, library_corroborated: bool = True) -> float:
    """plan.md's score1(tactic, function), graded 0 / 0.5 / 1.

      - PRESENT + library_corroborated -> 1.0
      - PRESENT, not corroborated      -> 0.5 (body exists, library claim unsupported)
      - WEAK (stub) / ABSENT           -> 0.0

    `library_corroborated` defaults to True so a caller holding only a status -
    and any record predating this field - keeps the original binary behaviour
    instead of being silently downgraded to 0.5.
    """
    if status != PRESENT:
        return 0.0
    return 1.0 if library_corroborated else 0.5


def score_tactic(func_scores: list[float]) -> float:
    """plan.md's score2 - the mean of score_func over the functions claimed for
    one tactic. Returns 0.0 if the tactic has no claimed functions.
    """
    if not func_scores:
        return 0.0
    return sum(func_scores) / len(func_scores)


def score_qa(tactic_scores: list[float]) -> float:
    """plan.md's score3 - the mean of score_tactic over the tactics under one
    Quality Attribute. Returns 0.0 if no tactics exist under the QA.
    """
    if not tactic_scores:
        return 0.0
    return sum(tactic_scores) / len(tactic_scores)


def _tactic_group(nfr_name: str) -> str:
    """Mapped to plan.md: QA classification from NFR ID.
    '1.x' -> 'performance', '2.x' -> 'availability', else 'other'.
    """
    for tok in nfr_name.split():
        if tok.startswith("1."):
            return "performance"
        if tok.startswith("2."):
            return "availability"
    return "other"


def build_scoring_hierarchy(results: list[dict]) -> dict:
    """Aggregates score_func -> score_tactic -> score_qa across all NFR entries.

    Returns:
      {
        "score_func":    { tactic_name: { function_ref: float } },
        "score_tactic":  { tactic_name: float },
        "score_qa":      { qa_name: float },
        "qa_tactics":    { qa_name: [tactic_names] },
        "overall_score": float
      }
    """
    tactic_fn_scores: dict[str, dict[str, float]] = {}
    qa_tactics_map: dict[str, set[str]] = {}

    for r in results:
        qa_group = r.get("qa_group", _tactic_group(r.get("nfr", "")))
        qa_tactics_map.setdefault(qa_group, set())

        tactics = r.get("tactics", [])
        functions = r.get("functions", [])

        for t in tactics:
            qa_tactics_map[qa_group].add(t)
            tactic_fn_scores.setdefault(t, {})
            for fn in functions:
                ref = fn["ref"]
                # "score1" is the pre-rename key: a report written before the
                # rename still aggregates correctly, with no re-run.
                sf = fn.get("score_func", fn.get("score1"))
                if sf is None:
                    sf = score_func(
                        fn.get("status", ABSENT),
                        fn.get("uses_any", False) or not fn.get("lib_claimed", True),
                    )
                tactic_fn_scores[t][ref] = sf

    tactic_scores: dict[str, float] = {}
    for t, fn_map in tactic_fn_scores.items():
        tactic_scores[t] = round(score_tactic(list(fn_map.values())), 4)

    qa_scores: dict[str, float] = {}
    for qa, t_set in qa_tactics_map.items():
        qa_scores[qa] = round(
            score_qa([tactic_scores[t] for t in t_set if t in tactic_scores]), 4
        )

    overall = round(
        sum(qa_scores.values()) / len(qa_scores) if qa_scores else 0.0, 4
    )

    return {
        "score_func": tactic_fn_scores,
        "score_tactic": tactic_scores,
        "score_qa": qa_scores,
        "qa_tactics": {qa: sorted(list(ts)) for qa, ts in qa_tactics_map.items()},
        "overall_score": overall,
    }


class StaticQualityAttributeValidator(IStaticQualityValidator):
    """
    Stage 3 – Static Quality Attribute (NFR trace) Validator:
    - Locates the NFR trace file inside the generated code dir
    - Verifies EXISTENCE only (no behavior): tactics resolve against the
      catalog, claimed files/functions exist and are non-trivial, and claimed
      libraries are imported and used
    - Computes the 3-tier hierarchy score_func -> score_tactic -> score_qa
      (plan.md Part 3's score1 / score2 / score3)
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
            qa_group = _tactic_group(entry.get("nfr", ""))
            r_status, r_ev, tactics = self._resolve(entry, known_tactics)
            if r_status != OK:
                # Functions claimed but unresolved -> ABSENT (score_func=0.0)
                functions = [
                    {"ref": ref, "status": ABSENT, "score_func": 0.0,
                     "detail": "tactic out-of-catalog"}
                    for ref in entry.get("functionNames", [])
                ]
                results.append({
                    "nfr": entry["nfr"],
                    "qa_group": qa_group,
                    "status": r_status,
                    "stage": "resolve",
                    "score_tactic": 0.0,
                    "evidence": r_ev,
                    "tactics": tactics,
                    "functions": functions,
                    "libraries": [],
                })
                continue

            l_status, l_ev, located = self._locate(entry, repo_root)
            if l_status != OK:
                # Functions claimed but files missing -> ABSENT (score_func=0.0)
                functions = [
                    {"ref": ref, "status": ABSENT, "score_func": 0.0, "detail": l_ev}
                    for ref in entry.get("functionNames", [])
                ]
                results.append({
                    "nfr": entry["nfr"],
                    "qa_group": qa_group,
                    "status": l_status,
                    "stage": "locate",
                    "score_tactic": 0.0,
                    "evidence": l_ev,
                    "tactics": tactics,
                    "functions": functions,
                    "libraries": [],
                })
                continue

            fn_details = _check_functions(entry, located)
            lib_details = _check_libraries(entry, located)
            fn_lib, level1 = _check_function_uses_library(entry, located)

            all_statuses = [st for _, st, _ in fn_details] + [st for _, st, _ in lib_details] + [level1]
            combined = _combine(all_statuses)

            link_by_ref = {i["ref"]: i for i in fn_lib}
            functions = []
            entry_func_scores = []
            for r, s, e in fn_details:
                link = link_by_ref.get(r, {})
                # No library claimed for this NFR -> nothing to corroborate, so the
                # function is not docked to 0.5 for a claim it never made.
                corroborated = link.get("uses_any", False) or not link.get("lib_claimed", True)
                sf = score_func(s, corroborated)
                entry_func_scores.append(sf)
                functions.append({
                    "ref": r,
                    "status": s,
                    "score_func": sf,
                    "detail": e,
                    "libraries_used": link.get("libs_used", []),
                    "uses_any": link.get("uses_any", False),
                    "lib_claimed": link.get("lib_claimed", False),
                })

            # score_tactic for this entry: sum(score_func) / num_functions
            entry_tactic_score = score_tactic(entry_func_scores)

            fn_str = "; ".join(
                f"{f['ref'].split('::')[-1]}={f['status']}(score_func={f['score_func']})"
                for f in functions
            )
            lib_str = "; ".join(f"{lib}={st}" for lib, st, _ in lib_details)
            link_str = "; ".join(f"{i['ref'].split('::')[-1]}->{i['libs_used'] or 'none'}" for i in fn_lib)
            evidence = f"functions[{fn_str}] libraries[{lib_str}] fn-uses-lib[level1={level1}; {link_str}]"

            results.append({
                "nfr": entry["nfr"],
                "qa_group": qa_group,
                "status": combined,
                "stage": "existence",
                "score_tactic": round(entry_tactic_score, 4),
                "evidence": evidence,
                "tactics": tactics,
                "functions": functions,
                "libraries": [{"lib": l, "status": s, "detail": e} for l, s, e in lib_details],
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
        run_dir = app_run_dir(self._report_dir, "static_qa", repo_root)
        path = run_dir / "static_qa_report.json"
        payload = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "trace_file": str(trace_path),
            "repo_root": str(repo_root),
            "scoring_summary": {
                "overall_score": counts.get("overall_score"),
                "score_qa": counts.get("score_qa"),
                "score_tactic": counts.get("score_tactic"),
                "score_func": counts.get("score_func"),
            },
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
            trace = json.loads(trace_path.read_text(encoding="utf-8-sig"))
        except Exception as e:
            return ValidationResult(
                stage="static_qa",
                status=Status.FAIL,
                message=f"Failed to read/parse NFR trace: {e}",
                details={"error": str(e)},
            )

        known_tactics = self._load_known_tactics()
        results = self._verify(trace, repo_root, known_tactics)

        # Build the hierarchy score_func -> score_tactic -> score_qa (plan.md Part 3)
        scoring = build_scoring_hierarchy(results)

        # Structure detailed tally by QA category
        tally: dict[str, dict] = {
            "overall_score": scoring["overall_score"],
            "score_qa": scoring["score_qa"],
            "score_tactic": scoring["score_tactic"],
            "score_func": scoring["score_func"],
            "qa_groups": {},
        }

        for r in results:
            g = r.get("qa_group", "other")
            bucket = tally["qa_groups"].setdefault(
                g,
                {
                    "score_qa": scoring["score_qa"].get(g, 0.0),
                    "tactics": scoring["qa_tactics"].get(g, []),
                    "nfrs": [],
                },
            )
            bucket["nfrs"].append({
                "nfr": r["nfr"],
                "tactics": r.get("tactics", []),
                "score_tactic": r.get("score_tactic", 0.0),
                "status": r.get("status"),
                "functions": [
                    {"ref": f["ref"], "status": f["status"],
                     "score_func": f.get("score_func", 0.0)}
                    for f in r.get("functions", [])
                ],
                "libraries": [
                    {"lib": lib["lib"], "status": lib["status"]}
                    for lib in r.get("libraries", [])
                ],
            })

        # Informational pass: Status.PASS if trace is valid and scored,
        # embedding every score_func/score_tactic/score_qa metric in details.
        status = Status.PASS
        message = (
            f"Static QA trace verified and scored: "
            f"overall={scoring['overall_score']}, score_qa={scoring['score_qa']}"
        )

        report_path = self._write_json_report(trace_path, repo_root, results, tally)
        self._update_history(trace)

        return ValidationResult(
            stage="static_qa",
            status=status,
            message=message,
            details={"tally": tally, "report_path": report_path,
                     "run_dir": str(Path(report_path).parent)},
        )

