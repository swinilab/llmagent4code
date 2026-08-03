# Reference application — evaluator calibration

Not a study artifact. This exists to answer one question about the evaluator:
**when it reports a red result, is that the application's fault or the
evaluator's?**

Without a system known to implement all six tactics, a scenario that fails for
all three generated applications is ambiguous — it could be a shared weakness in
the generated systems, or a bug in the measurement. This application removes the
ambiguity by being deliberately, plainly correct.

It is not an entrant, is not scored, and must never appear in the results.

## What it implements

All six prescribed tactics, and nothing more than they need:

| Scenario | Mechanism | Where |
|---|---|---|
| ASR-P1 | TTL cache with per-key single-flight refill | `app/cache.py` |
| ASR-P2 | Counting semaphore that refuses immediately | `app/admission.py` |
| ASR-A1 | PostgreSQL `statement_timeout` plus bounded connect timeout | `app/database.py` |
| ASR-A2 | Bounded retry with explicit fault classification | `app/database.py` |
| ASR-A3 | Stale-copy serving while the database is unreachable | `app/cache.py` |
| ASR-A4 | One transaction spanning payment, invoice and order | `app/services.py` |

Field-level validation is deliberately light. Reproducing the whole constraint
table would amount to doing the generation task, and G1 is not what this
calibrates — G3 is. Expect a mediocre G1 score here and ignore it.

## Running it

Host ports are offset by 10000 so this stack can run alongside an application
under evaluation, which occupies the standard ones. Inside the Docker network
the services still use their normal ports, so the deployment contract is
unchanged — only the evaluator's view from the host shifts.

| Service | Host port |
|---|---|
| app | 18080 |
| Toxiproxy API | 18474 |
| Toxiproxy postgres listener | 18666 |
| PostgreSQL | 15432 |

```bash
cd evaluator/reference_app && docker compose up --build -d && cd ../..

python -m evaluator.run \
  --app evaluator/reference_app \
  --app-id reference \
  --runs 1 \
  --base-url http://localhost:18080 \
  --dsn postgresql://orderman:orderman@localhost:15432/orderman
```

The Toxiproxy API port also has to be told about the offset; pass
`--toxiproxy-port 18474`.

All six scenarios should pass. Any that does not is an evaluator bug — fix the
evaluator, not this application.

## Deliberate-defect runs

A green result on a correct application only proves the evaluator does not
produce false failures. It says nothing about whether the evaluator would
*notice* a real violation — an assertion that never fires looks identical to one
that always passes.

Each switch below breaks exactly one mechanism, in the way a plausible-but-wrong
implementation would break it. Set it, re-run, and confirm the named scenario
goes red. If it stays green, that assertion is not doing its job.

| Variable | Breaks | Must fail | Caught by | Why it is subtle |
|---|---|---|---|---|
| `DEFECT_NO_SINGLE_FLIGHT` | concurrent misses each read the database | ASR-P1 | reads per concurrent refill | the cache works under light load, and aggregate reads stay in budget either way |
| `DEFECT_QUEUE_INSTEAD_OF_REJECT` | excess requests wait for a slot | ASR-P2 | rejection p95 above the client floor | admitted and rejected counts stay exactly right; only latency reveals it |
| `DEFECT_METRICS_NEED_DB` | `/internal/metrics` touches the database | ASR-A3 | metrics reachable during the outage | invisible until the outage, which is when it matters |
| `DEFECT_NO_DEGRADED_CACHE` | the warmed entry expires during the outage | ASR-A3 | warmed-read success rate | the first reads succeed; failures start once the TTL passes |
| `DEFECT_WRONG_ERROR_CODE` | timeout and unavailability report each other's code | ASR-A1, ASR-A3 | error-code classification | status codes stay plausible; only the classification is wrong |
| `DEFECT_PARTIAL_COMMIT` | payment commits before invoice and order | ASR-A4 | row statuses read over SQL | the API answers correctly; only direct SQL shows the divergence |

The "caught by" column is worth reading as a checklist of what each scenario is
really testing. Note that `METRICS_NEED_DB` and `NO_DEGRADED_CACHE` both break
ASR-A3 but trip different assertions -- one loses observability, the other loses
the degraded read itself -- so neither is masking the other.

### Calibration status

Both directions confirmed on the current evaluator:

- correct application: **6/6 scenarios pass** -- no false failures
- each defect: caught by its intended scenario, with no unexplained collateral

Observed values that make the point concrete:

| Defect | Assertion | Correct | Broken |
|---|---|---|---|
| `NO_SINGLE_FLIGHT` | reads per concurrent refill | 1 | 10 (one per reader) |
| `QUEUE_INSTEAD_OF_REJECT` | rejection p95 above floor | ~0 ms | seconds |
| `PARTIAL_COMMIT` | persisted row statuses | PENDING/ISSUED/PAID | VERIFIED/ISSUED/PAID |
| `NO_DEGRADED_CACHE` | warmed-read success rate | >= 99% | 0% |
| `METRICS_NEED_DB` | metrics during outage | reachable | unreachable |
| `WRONG_ERROR_CODE` | error classification | TIMEOUT / UNAVAILABLE | swapped |

Run them all with:

```powershell
.\evaluator\run_defects.ps1
```

Two things about how the switches are passed, both learned the hard way:

- Compose reads them from `evaluator/reference_app/.env`. A shell environment
  variable does not reach the container, and setting one produces a run that
  looks like a clean pass while no defect is active at all.
- Keep `--app-id` stable across runs. It determines the Compose project name,
  so changing it points the harness at a different stack and G0 fails for a
  reason unrelated to the defect.

Run one switch at a time. Combining them makes it impossible to tell which
assertion caught what.

## What calibration found

The first full run against this application returned 0/6, and every one of
those failures was in the evaluator or the harness rather than here. They are
worth recording, because each was invisible to unit tests:

| Symptom | Cause |
|---|---|
| all six FAIL at 1 run | the 5-run pass requirement applied literally to a 1-run session |
| `scenarioId` blank in the report | a snake_case field read as camelCase |
| ASR-P2 crashed | a probe thread shadowed `threading.Thread._stop` |
| ASR-A2 "0 database reads" | a primary-key lookup registers as no scan in `pg_stat` |
| ASR-P1 4% error rate | reads driven above `MAX_IN_FLIGHT_REQUESTS`, so P2 rejected P1's own workload |
| ASR-P2 rejections "2.4 s" | the client's own cost for opening 200 sockets, charged to the server |

The defect runs then found a **gap in the evaluator itself** — the failure mode
a green calibration is meant to rule out. With single-flight disabled, ASR-P1
still passed comfortably: over a thousand reads the handful of TTL refills cost
so little that a cache loading once per reader was indistinguishable from one
loading once per refill. The scenario now isolates a single refill and counts
what it costs, which is the only place the difference is visible.

That is the point of running the defects at all. An assertion that never fires
looks exactly like one that always passes, and only a deliberately broken
application tells the two apart.

Three real defects in this application also surfaced, none of which the unit
tests could reach:

| Symptom | Cause |
|---|---|
| ASR-A1 waited out the full 5 s | `statement_timeout` bounds execution, not network latency |
| ASR-A2 saw one attempt, not three | a worker thread inherits none of the caller's ContextVars |
| ASR-P2 rejections arrived seconds late | `time.sleep` in async middleware stalled the event loop |

The last is the clearest argument for having this application at all: the
semaphore was correct throughout, admitting exactly ten and refusing exactly
190, yet the scenario failed because a blocking sleep elsewhere prevented the
server from picking up the requests it was supposed to refuse instantly.
