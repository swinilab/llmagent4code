# Experimental Results — Generated OMS Backends

Measured results for the four generated applications in the corpus, across the four
validation stages of `method_pipeline_v2`. Every number here is reproducible from the JSON
artefacts committed alongside this file; each table cell links to the run that produced it.

| | |
|---|---|
| Measured on | 2026-08-31 |
| Corpus | 4 apps, all generated from [`prompts/latest.md`](../prompts/latest.md) |
| Environment | Windows 11, Python 3.12.10, Docker 28.0.4, uv 0.12.0 |
| Harness | `method_pipeline_v2`, stages 2 / 3 / 5 / 6 |

---

## 1. Corpus

All four apps were generated from the same prompt version. Prompt provenance was verified by
the `nfr-trace.json` schema, which `latest.md` fixes at exactly five keys (`nfr`,
`filesImplemented`, `librariesUsed`, `functionNames`, `tacticUsed`); an earlier prompt
generation produced nine. `apps/app-claude` was excluded on this basis — it carries the
nine-key schema and predates the final `latest.md` by one day.

| App | Path | Agent | Stack |
|---|---|---|---|
| `claude` | [`generated/claude`](../generated/claude) | Claude | FastAPI + Postgres (primary + streaming replica) + Redis |
| `codex` | [`generated/codex`](../generated/codex) | Codex | FastAPI + Postgres + Redis + Prometheus |
| `chatdev-v1` | [`generated/chatdev-qwen35-v1`](../generated/chatdev-qwen35-v1) | ChatDev / qwen3.5 | FastAPI + Postgres + Redis |
| `chatdev-v2` | [`generated/chatdev-qwen35-v2`](../generated/chatdev-qwen35-v2) | ChatDev / qwen3.5 | FastAPI + SQLite |

`generated/codex` is the only app carrying a byte-identical snapshot of the prompt it was
generated from (`generated/codex/latest.md`, 18,645 B), so it is the one app whose prompt
version is provable rather than inferred.

---

## 2. Results

| Stage | What it measures | `claude` | `codex` | `chatdev-v1` | `chatdev-v2` |
|---|---|---|---|---|---|
| **2 — Functional** | BVA/EP field constraints, 147 cases | **98.0%** | **97.3%** | 76.9% | **1.4%** |
| **6 — Workflow** | Lifecycle integration, 19 checks | **100%** | **100%** | 36.8% | 36.8% |
| **3 — Conformance** | NFR trace claims borne out by code, graded 0 / 0.5 / 1 | 0.818 | **0.984** | 0.781 | 0.587 |
| **5 — TICS** | Tactic conflict exposure (high = more) | 0.166 | 0.443 | 0.071 | 0.240 |
| **5 — pairs found** | Of the 13 conflicting tactic pairs | 5 | 13 | 3 | 11 |

Stages 2 and 6 are dynamic (live HTTP against the running app); stages 3 and 5 are static
(source analysis). Stages 2 and 6 are deliberately kept separate and never combined: stage 2 is
unit-level — one field constraint per case against one create endpoint — while stage 6 is
integration-level, checking whether the entities compose into the state machine the prompt
specifies.

### 2.1 Functional (stage 2) — 147 BVA/EP cases

| Entity | Cases | `claude` | `codex` | `chatdev-v1` | `chatdev-v2` |
|---|---|---|---|---|---|
| customer | 50 | 49 (98.0%) | 48 (96.0%) | 45 (90.0%) | 0 (0.0%) |
| product | 25 | 25 (100%) | 25 (100%) | 25 (100%) | 2 (8.0%) |
| order | 28 | 28 (100%) | 28 (100%) | 16 (57.1%) | 0 (0.0%) |
| payment | 18 | 16 (88.9%) | 16 (88.9%) | 9 (50.0%) | 0 (0.0%) |
| invoice | 26 | 26 (100%) | 26 (100%) | 18 (69.2%) | 0 (0.0%) |
| **total** | **147** | **144** | **143** | **113** | **2** |

Artefacts: [claude](functional_test_claude_20260831_122237/functional_test_report.json) ·
[codex](functional_test_codex_20260831_123107/functional_test_report.json) ·
[chatdev-v1](functional_test_chatdev-qwen35-v1_20260831_133454/functional_test_report.json) ·
[chatdev-v2](functional_test_chatdev-qwen35-v2_20260831_151146/functional_test_report.json)

### 2.2 Workflow (stage 6) — 19 integration checks

Three sub-scores, because "route absent" and "route present but broken" are different defects.

| Category | Checks | `claude` | `codex` | `chatdev-v1` | `chatdev-v2` |
|---|---|---|---|---|---|
| capability — route published per lifecycle step | 7 | 7 | 7 | 7 | 7 |
| happy path — `PLACED`→`ACCEPTED`→`INVOICED`→`PAID`→`VERIFIED`→`SHIPPED`→`CLOSED` | 7 | 7 | 7 | 0 | 0 |
| precondition — out-of-order transition rejected with 409 | 5 | 5 | 5 | 0 | 0 |
| **total** | **19** | **19** | **19** | **7** | **7** |

Every state assertion is made by re-reading the entity, not by trusting the transition's HTTP
status. Both ChatDev apps publish the complete route set and satisfy none of it.

Artefacts: [claude](workflow_test_claude_20260831_122254/workflow_test_report.json) ·
[codex](workflow_test_codex_20260831_123139/workflow_test_report.json) ·
[chatdev-v1](workflow_test_chatdev-qwen35-v1_20260831_133519/workflow_test_report.json) ·
[chatdev-v2](workflow_test_chatdev-qwen35-v2_20260831_151632/workflow_test_report.json)

### 2.3 TICS (stage 5)

| | `claude` | `codex` | `chatdev-v1` | `chatdev-v2` |
|---|---|---|---|---|
| TICS (exposure, not quality) | 0.166 | 0.443 | 0.071 | 0.240 |
| interacting pairs `n+` | 5/13 | 13/13 | 3/13 | 11/13 |
| coverage | 0.492 | 1.000 | 0.227 | 0.811 |
| intensity | 0.338 | 0.443 | 0.314 | 0.296 |
| median witness distance | 2 | 1 | 3 | 2 |

Coverage × intensity = TICS exactly. Conformance is stage 3's and is reported in §2, not here:
it moved out of stage 5 with the formula change in §5.1.

No run was degraded (`"degraded": false` in all four reports); every pair score was computed
from stage 3's graded `score_func` confidences rather than the trace-only fallback. Each
non-zero pair keeps its witness functions and hop path in `tics_report.json`, so every number
above opens directly onto the source it came from.

Artefacts: [claude](tics_claude_20260831_165809/tics_report.json) ·
[codex](tics_codex_20260831_165817/tics_report.json) ·
[chatdev-v1](tics_chatdev-qwen35-v1_20260831_165753/tics_report.json) ·
[chatdev-v2](tics_chatdev-qwen35-v2_20260831_165801/tics_report.json)

Conformance artefacts (stage 3):
[claude](static_qa_claude_20260831_165805/static_qa_report.json) ·
[codex](static_qa_codex_20260831_165813/static_qa_report.json) ·
[chatdev-v1](static_qa_chatdev-qwen35-v1_20260831_165750/static_qa_report.json) ·
[chatdev-v2](static_qa_chatdev-qwen35-v2_20260831_165757/static_qa_report.json)

---

## 3. Failure attribution

Raw failure counts overstate defect counts, because one broken component cascades through every
case that depends on it. Failures are therefore classified as **independent** (a distinct
defect) or **cascade** (downstream of another failure).

| App | Failures | Independent defects | Cascade |
|---|---|---|---|
| `claude` | 3 | 1 + 2 disputed | 0 |
| `codex` | 4 | 1 + 3 disputed | 0 |
| `chatdev-v1` | 34 | 6 | 18 |
| `chatdev-v2` | 145 | 4 | ~141 |

### `claude` — 3 failures

| Case | Expected → actual | Verdict |
|---|---|---|
| `TC_CUS_PHONE_07` | 400 → 201 | **Defect.** Accepts `+8401234567`. The regex `^\+?[1-9]\d{7,14}$` admits it; the accompanying semantic rule *"must not start with 0 after country code"* is not implemented. |
| `TC_PAY_AMOUNT_02` | 409 → 400 | **Disputed** — see §3.5 |
| `TC_PAY_AMOUNT_03` | 409 → 400 | **Disputed** — see §3.5 |

### `codex` — 4 failures

| Case | Expected → actual | Verdict |
|---|---|---|
| `TC_CUS_ORDERHIST_01` | 400 → 201 | **Defect.** Accepts a client-supplied `orderHistory`, which the constraint table marks read-only / server-derived. |
| `TC_CUS_ID_04` | 405 → 400 | **Disputed.** `GET /customers/` returns 400 *"A UUIDv4 resource identifier is required"* rather than 405. The prompt does not assign a code to this case. |
| `TC_PAY_AMOUNT_02/03` | 409 → 400 | **Disputed** — see §3.5 |

### `chatdev-v1` — 34 failures, 6 independent

| Group | Count | Cause |
|---|---|---|
| `lineItems` validation | 8 | Rejects a valid order body with `lineItems[0]: productRef: Must be a string` — while `productRef` **is** a string (`"96946add-a0ee-489b-a971-7c1268bcdd14"`). The app's own validator is wrong. |
| cascade of the above | 18 | Order creation is impossible, so every FK-dependent order/payment/invoice case fails (12 seed-unavailable, 6 unresolved placeholder). |
| `orderHistory` accepted | 3 | `TC_CUS_ORDERHIST_01/02/03`, 400 → 201. Same class as codex's. |
| phone semantic rule | 1 | `TC_CUS_PHONE_07`, 400 → 201. Identical to claude's. |
| `TC_CUS_ID_04` | 1 | 405 → 500, `AttributeError` — an unhandled crash, not a routing choice. |
| `TC_INV_ORDERREF_03` | 3 | 404 → 422: requires a client-supplied `billingInfo`, which the spec defines as a server-side snapshot. |

The same `lineItems` defect is what blocks stage 6 entirely: `WF_H_01_PLACE` records
`actual = "order not created"`, so happy-path and precondition score 0.

### `chatdev-v2` — 145 failures, 4 independent defects

All four were located by reading the source and the server log; each is independently fatal.
Full analysis in [`executability/chatdev-v2.md`](executability/chatdev-v2.md).

| Defect | Effect |
|---|---|
| `\p{L}` — a PCRE escape unsupported by Python's `re` — in the name validator | every customer create raises at pattern-compile time |
| `RateLimiter._window_seconds` never assigned in `__init__` | `AttributeError` on every rate-limited call |
| Ambiguous FK between `orders` and `invoices`, no `foreign_keys=` | SQLAlchemy mappers never configure; every read → 503 |
| `exc.errors()` passed to `JSONResponse` unencoded | Pydantic v2's live `ValueError` is unserialisable, so 400s surface as 500s |

Only 2 of 147 cases pass. Seeding fails at the first request, so the remaining ~141 failures
are cascade.

### 3.5 Disputed expectation: payment amount mismatch

`TC_PAY_AMOUNT_02/03` expect **409** for a payment whose amount differs from the invoice total.
`claude` and `codex` both return **400**, with an explicit message (*"payment amount must
exactly equal the invoice total"*).

The prompt assigns 409 to *referential state* validation — *"paying against a non-`INVOICED`
order"* — and does not assign a code to a value mismatch, which falls under its field-validation
rules (400). Two independently generated applications converging on the same answer is evidence
that the test expectation, not the implementations, is the outlier. These 4 cases are reported
but flagged; resolving them would move `claude` to 99.3% and `codex` to 98.6%.

---

## 4. Executability

Changes required to make each app run, counted against the published artefact.

| App | Changes to run | Kind |
|---|---|---|
| `claude` | 0 | CRLF line endings in `deploy/*.sh` broke the shebang on a Windows checkout; the committed blobs are LF and a clone starts on Linux unmodified. Classified as environment. |
| `codex` | 1 line | `docker-compose.yml` declared no build target, so Docker built the Dockerfile's final `test` stage (`CMD ["pytest"]`) instead of `runtime`. Added `target: runtime`. |
| `chatdev-v1` | 1 line | `iac/init_db.sql` (128 lines, full schema) was never mounted into the Postgres container, and the app has no `create_all` or migration. Every query hit `UndefinedTable`. Added the `docker-entrypoint-initdb.d` mount. |
| `chatdev-v2` | not reachable by configuration | Four independent source-level defects. |

No application source was modified in any case. Details:
[`executability/codex.md`](executability/codex.md) ·
[`executability/claude-latest.md`](executability/claude-latest.md) ·
[`executability/chatdev-v2.md`](executability/chatdev-v2.md)

**`chatdev-v1` is reported twice** because the one-line fix changes what is being measured:

| | as generated | after the 1-line IaC fix |
|---|---|---|
| functional | 81/147 = 55.1% | 113/147 = 76.9% |
| customer | 50.0% | 90.0% |
| product | 60.0% | 100% |

The as-generated figure measures a missing schema; the post-fix figure measures the validation
logic. Both are given because `codex` received the same treatment before being measured, and
applying the fix to one app but not the other would be two standards for one class of defect.

Both runs are retained:
[as generated](functional_test_chatdev-qwen35-v1_20260831_132103/functional_test_report.json) ·
[after the fix](functional_test_chatdev-qwen35-v1_20260831_133454/functional_test_report.json).
The second is the one reported in §2.

---

## 5. Observations

**Conformance does not discriminate on executable quality.** `chatdev-v1` scores **0.781** on
stage 3 — within 0.04 of `claude`'s 0.818 — while passing 76.9% of functional cases against
`claude`'s 98.0%, and 36.8% of workflow checks against 100%. Stage 3 verifies that claimed
files, functions and libraries exist, are non-trivial, and are actually referenced by the
function that claims them; it performs no behavioural check, by design. An agent that writes a
truthful `nfr-trace.json` over broken code still scores well. Stage 3 is a necessary
anti-fabrication check, not a quality measure.

Until 2026-08-31 stage 3 was binary (present / absent) and saturated: 100 of 101 functions
across the corpus scored 1.0, and three of the four apps tied at exactly 1.0. The per-function
score (`score_func`, plan.md's `score1`) is now
graded 0 / 0.5 / 1, the middle level marking a function whose body exists but references none
of the libraries its own trace entry claims. The four apps separate over 0.587–0.984; the
observation above survives the change, the saturation does not. Two defects found while
grading are recorded in §6.

**A startup banner is not executability.** All four apps start and answer a health probe.
`chatdev-v1` passed its container healthcheck with an empty database; `chatdev-v2` returns 200
on `/health` while every business endpoint fails. Any oracle whose success condition is "the
process started" cannot separate these apps — which is precisely the condition ChatDev's own
in-workflow test phase uses (see [`executability/chatdev-v2.md`](executability/chatdev-v2.md) §3).

**TICS is dominated by coverage, and must not be read alone.** TICS factors exactly into
coverage × intensity. Across the corpus intensity stays inside 0.30–0.44 while coverage ranges
0.23–1.00, so the product tracks coverage almost entirely:

| | `claude` | `codex` | `chatdev-v1` | `chatdev-v2` |
|---|---|---|---|---|
| TICS | 0.166 | 0.443 | 0.071 | 0.240 |
| coverage | 0.492 | 1.000 | 0.227 | 0.811 |
| intensity | 0.338 | 0.443 | 0.314 | 0.296 |
| pairs found | 5/13 | 13/13 | 3/13 | 11/13 |

`chatdev-v1` has the *lowest* TICS (0.071) and the worst workflow result among the systems that
run: it earns that score by exposing an interaction in only 3 of 13 pairs — a thin
implementation, not a clean one. `codex`, with the highest conformance, has the highest TICS,
because tactics it did not build could not have collided. Always read TICS beside conformance
and the pairs-found count.

**Capability and correctness separate cleanly at the integration level.** Both ChatDev apps
publish 7/7 lifecycle routes and satisfy 0/12 behavioural checks. A route inventory — or an
OpenAPI-based conformance check — would score them full marks.

---

## 5.1 Formula change, 2026-08-31

The TICS formula was simplified after the numbers above were first produced. The measure is now
four lines:

```
conf_func(t, f)          = stage 3's score_func(t, f)                    in {0, 0.5, 1}
conf_pair(t1,t2, f1,f2)  = sqrt(conf_func(t1,f1) * conf_func(t2,f2)) / (1 + d(f1,f2))
conf_tactic(t1, t2)      = max over every (f1, f2)
TICS                     = sum(w * conf_tactic) / sum(w)   over the 13 pairs with w > 0
```

Removed: the exponential decay `exp(-0.35(d-1))`, the `wired()` degree test, the
implementation-conditioned denominator, the sampled reference baseline and the proximity lift,
and the `breadth`/`intensity` pair as reported metrics (they survive as the two factors of the
decomposition above). Conformance moved out of stage 5 entirely — it is stage 3's
`score_func → score_tactic → score_qa` hierarchy, which is why the conformance row now cites
stage 3.

The ordering of the four systems is unchanged by the simplification. It was checked against
four variants of the decay and aggregation rules before the form above was fixed; all four
produce `codex > chatdev-v2 > claude > chatdev-v1`, so the choice affects the scale and the
interpretability, not the ranking. The hop bound `d_max = 6` never binds on this corpus:
every pair found at all is found within three hops, and removing the bound entirely leaves all
four scores unchanged to four decimal places.

---

## 6. Measurement corrections

An earlier result set exists at `docs/reports_results_270826` (2026-08-27). **It is superseded
and should not be cited.** Four harness defects were found and fixed while producing the results
above; each inflated the failure count of the app under test rather than the harness's own.

The pre-grading stage 3 and stage 5 runs were also removed from the working tree: five
`static_qa_*` runs scoring 1.0 / 0.9584 under the binary per-function score, and five `tics_*`
runs carrying the superseded schema (`breadth`, `intensity`, `proximityLift`, `applicableMass`,
and a `conformance` field that stage 5 no longer owns). They were deleted rather than kept
because the validator sources that produced them no longer exist in this repository — an
artefact the shipped code cannot regenerate is worse than no artefact, since a reader who
re-runs gets different numbers with no way to tell which is the defect. They remain recoverable
from git history at commit `e315928` (`git show e315928:<path>`). The table that formerly stood
in §2.3 was a verbatim transcription of those five deleted `tics_report.json` files, which is
how it came to contradict §2 and §5.

| Defect | Effect on the earlier numbers |
|---|---|
| Seeding refused any state transition not declared in `workflow_apis.json` — a file `latest.md` never asks for | 15 of codex's 17 failures were harness artefacts. Transition routes are now inferred from the app's own OpenAPI and verified by re-reading the entity's state. Codex: 88.4% → 97.3% |
| Invoice and payment cases shared one seeded order | A negative case fired at an already-consumed order is answered by the app's state check before the field rule under test is reached, so the outcome tracked the app's internal validation order. Every case now gets its own untouched order. |
| Stage 6 returned early when actors could not be created | An app whose every request failed scored 7/7 = **100%**. The suite now emits the full 19-check set with reasons, keeping the denominator constant across apps. |
| Stages 2 and 6 resolved the code path differently from stages 3 and 5 | No single config value could run all four stages; two of them reported "NFR trace file not found" against a file that existed. |
| Stage 3's method→class index was keyed by bare name (`get`) while traces address methods qualified (`EntityCache.get`) | Every qualified lookup missed, disabling the `self.<attr>` credit entirely. Invisible while the per-function score was binary; once graded it cost `claude` 12 points and `codex` 8 (`claude` 0.693 → 0.818, `codex` 0.901 → 0.984). |
| Stage 3 resolved `self.<attr>` to a library only through class-scope assignments (`self._q = asyncio.Queue()`) | Constructor injection — `def __init__(self, redis: Redis)` then `self._redis = redis` — names the library only in the annotation, so injected dependencies read as absent. The fix penalised DI relative to inline construction, i.e. a coding style rather than a difference in conformance. |

The comparison in the earlier set was also confounded: it measured `apps/app-claude`, generated
from an older prompt that *did* require `workflow_apis.json`, against `codex`, generated from
`latest.md` which does not. The 10-point gap was mostly that asymmetry.

---

## 7. Threats to validity

- **`claude/workflow_apis.json` was added by hand** (commit `5180730`), not generated. Its
  presence is why claude's seeding used declared routes while codex's used inferred ones. The two
  paths were shown to be equivalent — running claude with the manifest suppressed yields the same
  19/19 — but the asymmetry in the artefacts remains.
- **Transition discovery is heuristic.** Two route shapes are recognised: a dedicated action
  route (`POST {orders}/{id}/accept`) and a generic status setter (`PUT {orders}/{id}/status`
  with the target status in the body). Both occur in the corpus. An app using a third shape
  would be scored as lacking the capability. The re-read verification prevents a
  mis-identified route from producing a false pass, but not a false absence.
- **Stage 3 does not follow indirection.** A function reaches its claimed library directly, or
  through a `self.<attr>` the class assigns or has injected. It is not traced through a
  module-level helper: `claude`'s `PaymentService.create` opens a `unit_of_work()` and works
  through repositories, so its `sqlalchemy` claim is honoured one layer down and scores 0.5.
  This is a floor on the reported score, never a ceiling — the analysis cannot invent evidence,
  only miss it.
- **Four disputed expectations** (§3.5, and codex's `TC_CUS_ID_04`) rest on codes the prompt
  does not specify.
- **Single run per app.** No repetition, so run-to-run variance is unmeasured. The one
  repeated configuration (claude, run three times during harness development) returned 144/147
  each time, including against a database already populated by a previous run.
- **Corpus size is 4**, spanning 3 agents; `chatdev-v1` and `chatdev-v2` share an agent and a
  prompt but differ in outcome, which limits per-agent claims.
- **Python only.** All four apps are Python, so TICS's extractor coverage is not exercised on
  another language.
