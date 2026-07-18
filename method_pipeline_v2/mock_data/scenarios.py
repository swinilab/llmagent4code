"""
mock_data/scenarios.py
───────────────────────
Pre-baked scenarios for exercising every branch of the pipeline.

Each scenario has:
  code    – what the generation agent "returns" on first call
  repairs – ordered list of code strings the repair agent tries (k attempts)

Sentinel tokens understood by mock validators:
  # MOCK:COMPILE_FAIL      → MockCompilabilityValidator returns FAIL
  # MOCK:FUNCTIONAL_FAIL   → MockFunctionalValidator returns FAIL

Run a specific scenario via CLI:
  python main.py --scenario all_pass
  python main.py --scenario compile_fail_then_fix
  python main.py --scenario functional_fail_then_fix
  python main.py --scenario exceed_repair_limit
"""

# ── Boilerplate included in every "good" code blob ───────────────────────────

_GOOD_CODE = '''\
# Generated FastAPI service
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()
_store: dict[int, dict] = {}
_counter = 0

class Item(BaseModel):
    name: str
    value: int

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/items", status_code=201)
def create_item(item: Item):
    global _counter
    _counter += 1
    _store[_counter] = item.dict()
    return {"id": _counter, **item.dict()}

@app.get("/items/{item_id}")
def get_item(item_id: int):
    if item_id not in _store:
        raise HTTPException(status_code=404, detail="not found")
    return {"id": item_id, **_store[item_id]}
'''

_CODE_WITH_SYNTAX_ERROR = '''\
# MOCK:COMPILE_FAIL
from fastapi import FastAPI
app = FastAPI(

@app.get("/health")   # SyntaxError: missing closing paren above
def health():
    return {"status": "ok"}
'''

_CODE_WITH_FUNCTIONAL_ERROR = '''\
# MOCK:FUNCTIONAL_FAIL
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Item(BaseModel):
    name: str
    value: int

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/items", status_code=201)
def create_item(item: Item):
    raise Exception("Not implemented yet")   # causes 500

@app.get("/items/{item_id}")
def get_item(item_id: int):
    return {}
'''

# ─────────────────────────────────────────────────────────────────────────────
#  Scenario definitions
# ─────────────────────────────────────────────────────────────────────────────

MOCK_SCENARIOS: dict[str, dict] = {

    # ── 1. Everything works first try ────────────────────────────────────────
    "all_pass": {
        "code":    _GOOD_CODE,
        "repairs": [],          # never reached
    },

    # ── 2. Compile fails, repair fixes it on iteration 1 ─────────────────────
    "compile_fail_then_fix": {
        "code": _CODE_WITH_SYNTAX_ERROR,
        "repairs": [
            _GOOD_CODE,         # repair #1 → good code, passes compile + functional
        ],
    },

    # ── 3. Compile passes, functional fails, repair fixes on iteration 1 ─────
    "functional_fail_then_fix": {
        "code": _CODE_WITH_FUNCTIONAL_ERROR,
        "repairs": [
            _GOOD_CODE,         # repair #1 → good code
        ],
    },

    # ── 4. Repair loop exhausted (compile fails, repairs never fully fix it) ─
    "exceed_repair_limit": {
        "code": _CODE_WITH_SYNTAX_ERROR,
        "repairs": [
            _CODE_WITH_SYNTAX_ERROR,    # repair #1 → still broken
            _CODE_WITH_SYNTAX_ERROR,    # repair #2 → still broken
            _CODE_WITH_SYNTAX_ERROR,    # repair #3 → still broken  (k=3 exhausted)
        ],
    },

    # ── 5. Compile passes, functional fails and is never fixed ───────────────
    "functional_fail_no_fix": {
        "code": _CODE_WITH_FUNCTIONAL_ERROR,
        "repairs": [
            _CODE_WITH_FUNCTIONAL_ERROR,   # repair #1 → still broken
            _CODE_WITH_FUNCTIONAL_ERROR,   # repair #2 → still broken
        ],
    },

    # ── default (alias for all_pass) ─────────────────────────────────────────
    "default": {
        "code":    _GOOD_CODE,
        "repairs": [],
    },
}
