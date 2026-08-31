App is running. It boots cleanly but **every business endpoint fails** — here's what I found.

## Launch

```bash
cd method_pipeline_v2/generated/chatdev-qwen35-v2/code_workspace
uv run python main.py          # start_command.txt
```

`uv` created `.venv` and installed 21 packages from `uv.lock`, then:

```
INFO:  Application startup complete.
INFO:  Uvicorn running on http://0.0.0.0:8080
```

Working: `GET /health` → `{"status":"healthy"}`, `GET /api/v1/openapi.json` → 200 (29 routes), `/docs` → 200. Note the OpenAPI URL is overridden to `/api/v1/openapi.json`, so plain `/openapi.json` is a 404.

## Smoke test results

| Request | Result |
|---|---|
| `GET` all 5 list endpoints | **503** DATABASE_ERROR |
| `POST /api/v1/customers` | **500** INTERNAL_ERROR |
| `POST /api/v1/products` | **500** INTERNAL_ERROR |
| `POST /api/v1/orders` | **500** INTERNAL_ERROR |

## Four distinct bugs

**1. SQLAlchemy mapper never configures — kills all reads** ([database.py:79](../method_pipeline_v2/generated/chatdev-qwen35-v2/code_workspace/oms/infrastructure/database.py#L79), [:120](../method_pipeline_v2/generated/chatdev-qwen35-v2/code_workspace/oms/infrastructure/database.py#L120))

`orders.invoice_ref → invoices.id` and `invoices.order_ref → orders.id` are two FK paths between the same pair of tables, and neither `relationship()` passes `foreign_keys=`.

```
Could not determine join condition between parent/child tables on
relationship OrderModel.invoice - there are multiple foreign key paths
```

`init_db()` doesn't trip this (`create_all` doesn't configure mappers), so startup looks healthy and the failure only appears on the first query.

**2. PCRE syntax in a Python regex** ([models.py:72](../method_pipeline_v2/generated/chatdev-qwen35-v2/code_workspace/oms/domain/models.py#L72), same at [:106](../method_pipeline_v2/generated/chatdev-qwen35-v2/code_workspace/oms/domain/models.py#L106))

```python
if not re.match(r'^[\p{L} .\'-]+$', value, re.UNICODE):   # re.error: bad escape \p
```

`\p{L}` is not supported by `re` (that's the `regex` module). Any customer create hits this — name validation raises before validation can pass. `re.UNICODE` is a no-op on str patterns.

**3. `RateLimiter._window_seconds` never assigned** ([rate_limiter.py:38](../method_pipeline_v2/generated/chatdev-qwen35-v2/code_workspace/oms/infrastructure/event/rate_limiter.py#L38))

`__init__` sets `_max_events` and `_events` but not `_window_seconds`, though `is_allowed()` and `get_remaining()` both read it → `AttributeError` on every rate-limited call. `config.rate_limit_window_seconds` exists and is simply never wired up. This is the NFR 1.1 tactic — it fails 100% closed.

**4. Validation handler masks 400s as 500s** ([exceptions.py:66-77](../method_pipeline_v2/generated/chatdev-qwen35-v2/code_workspace/oms/infrastructure/exceptions.py#L66-L77))

It puts raw `exc.errors()` into `JSONResponse`, but Pydantic v2 embeds a live `ValueError` in `ctx`:

```
TypeError: Object of type ValueError is not JSON serializable
```

So a legitimate 400 becomes a 500 with the details swallowed. Needs `exc.errors()` scrubbed (or `jsonable_encoder`).

Bugs 2–4 are each independently fatal to writes; bug 1 is fatal to reads.

---

## Evidence the workflow ended normally

| Check | Result |
|---|---|
| Run duration | 42 minutes (00:04:23 → 00:47:10), 538 calls |
| Final node | `Chief Executive Officer` exec 13–14, outputs of 459 and 421 tokens — a natural ending, not a mid-stream cut |
| `max output_tokens` | 8778, no repeated value above 1000 tokens |
| `max input_tokens` | 61,035 (p95 = 53,987) |
| Syntax of 32 `.py` files | `py_compile` clean, 100% |
| `manual.md` (30 KB) | ends with the proper `*Document Version: 1.0.0*` block |

The two rows that matter most: if `max_tokens` had cut it off, `output_tokens` would cluster on a repeated round number (4096/8192…) — here every large value is distinct. If it had been interrupted, some file would be truncated mid-function → `SyntaxError`. Neither happened. `ARCHITECTURE.md`, `DEPLOYMENT.md`, `manual.md`, `nfr-trace.json` are all present and complete — meaning the workflow reached the Manual Phase, its final phase.

## The real cause: the test oracle cannot reach it

This is the part that matters. See [chatdev.yaml:253-259](../method_pipeline_v2/agents/chatdev.yaml#L253-L259):

```
Test Reports: You should use `uv_run` function to run the code...

[CRITICAL INSTRUCTION FOR TIMEOUTS]
1. **Pass**: If the logs indicate the application started successfully
   (e.g., "Game started", "Listening on port", or simply running without
   crashing) and was eventually killed by the timeout,
   **DO NOT classify this as a bug**.
```

And the test node's tool list ([chatdev.yaml:231-240](../method_pipeline_v2/agents/chatdev.yaml#L231-L240)) is only `uv_related:All` plus file read/write tools. **No HTTP client.** The test agent cannot send a single request.

So for a server app, the ceiling of the test phase is exactly: *does `python main.py` print a banner?* This app prints `Uvicorn running on http://0.0.0.0:8080` → timeout → per the instruction, **PASS**.

`oms.db` confirms it: all 6 tables were created (`init_db()` ran fine), and **0 rows in every table**. The app was started; it was never called.

## All four bugs live behind the first request

None of them carries the signature of an unfinished generation:

- `\p{L}` ([models.py:72](../method_pipeline_v2/generated/chatdev-qwen35-v2/code_workspace/oms/domain/models.py#L72)) — PCRE syntax mistaken for the `re` module. A knowledge error; the code is complete and carries a proper explanatory comment right above it.
- `_window_seconds` ([rate_limiter.py:38](../method_pipeline_v2/generated/chatdev-qwen35-v2/code_workspace/oms/infrastructure/event/rate_limiter.py#L38)) — a complete 82-line file; `__init__` sets 2 attributes and forgets a 3rd that 2 other methods read. An internal-consistency error, not a truncation.
- Ambiguous FK `orders ↔ invoices` ([database.py:79](../method_pipeline_v2/generated/chatdev-qwen35-v2/code_workspace/oms/infrastructure/database.py#L79)) — a schema design error, and `create_all` does not trigger it; only a query does.
- `exc.errors()` not serializable ([exceptions.py:66-77](../method_pipeline_v2/generated/chatdev-qwen35-v2/code_workspace/oms/infrastructure/exceptions.py#L66-L77)) — a Pydantic v2 gotcha.

51 `Programmer Coding` + 203 `Code Reviewer` + 23 `Test Error Summary` invocations all ran; the problem is that the review/test loop had no signal to hold onto, because no one ever sent a request. It iterated against an oracle that always returns PASS.

To measure this properly, the test phase needs a real smoke test: start the server in the background → POST to the 5 endpoints in `create_apis.json` → assert 2xx. That is also the condition for the pipeline's pass-rate numbers to mean anything.
