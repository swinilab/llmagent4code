# Verification Steps — Observing Each NFR

Every command below was run against the stack started by
`docker compose up --build -d`; the outputs shown are the **actual observed
results**, not illustrations.

---

## NFR 1.1 — Limit Event Response

Fire 200 concurrent requests under one client identity against a bucket of
capacity 100 refilling at 50/s:

```bash
python - <<'EOF'
import threading, urllib.request, urllib.error, collections
codes, lock, start = collections.Counter(), threading.Lock(), threading.Barrier(200)
def hit():
    req = urllib.request.Request('http://localhost:8000/api/v1/customers/00000000-0000-4000-8000-000000000000')
    req.add_header('X-Client-Id', 'burst')
    start.wait()
    try:
        with urllib.request.urlopen(req, timeout=20) as r: c = r.status
    except urllib.error.HTTPError as e: c = e.code
    with lock: codes[c] += 1
ts = [threading.Thread(target=hit) for _ in range(200)]
[t.start() for t in ts]; [t.join() for t in ts]
print(dict(codes))
EOF
```

**Observed:** `{404: 139, 429: 61}` — 61 requests rejected above the ceiling.
(404 is the expected answer for the non-existent probe id; the point is the
429 split.) Throttled responses carry `Retry-After`.

The limit is enforced *globally* rather than per-worker — the API runs 4 uvicorn
workers, and the bucket lives in Redis behind an atomic Lua script. Confirm the
running counter:

```bash
curl -s localhost:8000/ops/nfr | jq .nfr_1_1_limit_event_response
```

---

## NFR 1.2 — Maintain Multiple Copies of Data

**Copy 1 & 2 — replication.** The standby is a real streaming replica:

```bash
docker exec oms-postgres-primary psql -U oms -d oms -tAc \
  "SELECT application_name||' state='||state||' sync='||sync_state FROM pg_stat_replication;"
docker exec oms-postgres-replica psql -U oms -d oms -tAc "SELECT pg_is_in_recovery();"
```

**Observed:** `walreceiver state=streaming sync=async` and `t` — the replica is
in recovery, i.e. genuinely read-only.

Data is present on both nodes:

```bash
docker exec oms-postgres-primary psql -U oms -d oms -tAc "SELECT count(*) FROM customers;"
docker exec oms-postgres-replica psql -U oms -d oms -tAc "SELECT count(*) FROM customers;"
```

**Observed:** `1` and `1` — identical.

**Copy 3 — cache.** Read the same entity twice and watch the counters move:

```bash
curl -s localhost:8000/api/v1/customers/$CUST > /dev/null   # populates
curl -s localhost:8000/api/v1/customers/$CUST > /dev/null   # served from cache
curl -s localhost:8000/ops/nfr | jq .nfr_1_2_multiple_copies
```

---

## NFR 2.1 — Exception Detection

**System exceptions.** Every unhandled fault becomes a structured response with
a correlation id, and expected faults map to the documented codes:

```bash
curl -s -o /dev/null -w "%{http_code}\n" localhost:8000/api/v1/orders/not-a-uuid          # 400
curl -s -o /dev/null -w "%{http_code}\n" localhost:8000/api/v1/orders/$(uuidgen)          # 404
curl -s -o /dev/null -w "%{http_code}\n" -X POST localhost:8000/api/v1/orders/$ORDER/ship # 409 when unverified
```

**Observed:** 400 / 404 / 409 respectively, for all five entities.

**Timeout detection.** Stop a dependency and the readiness probe names exactly
which component failed, rather than reporting a generic outage:

```bash
docker compose stop redis
curl -s localhost:8000/health/ready
```

**Observed:** `{"ready":true,"checks":{"primary":"up","replica":"up","redis":"down: ConnectionError"}}`

Note `ready:true` — the critical path does not require Redis. That is NFR 2.2,
below. Timeouts are bounded at three levels: 10 s per request (→504), 3 s per
Postgres statement, 250 ms per Redis call.

---

## NFR 2.2 — Graceful Degradation

**With the cache down, the whole workflow still works:**

```bash
docker compose stop redis
# then run the full 7-step workflow from DEPLOYMENT.md
```

**Observed, with Redis stopped:**

```
create customer w/o redis : 201
create product  w/o redis : 201
place order     w/o redis : 201  total= 50.00
accept order    w/o redis : 200  ACCEPTED
read order      w/o redis : 200  (cache bypassed)
```

**With the replica down, reads fall back to the primary:**

```bash
docker compose stop postgres-replica
```

**Observed:** `create customer w/o replica: 201`, `read customer w/o replica: 200`,
and readiness reports `"replica":"down: OperationalError"` while still
`ready:true`.

**Critical features cannot be shed.** Non-critical ones can:

```bash
curl -s -X POST localhost:8000/ops/degrade/cache_acceleration   # 200, feature SHED
curl -s -X POST localhost:8000/ops/degrade/order_workflow       # 400, refused
curl -s localhost:8000/ops/nfr | jq .nfr_2_2_graceful_degradation
```

Restore with `curl -s -X POST localhost:8000/ops/restore/cache_acceleration`.

---

## NFR 2.3 — State Resynchronization

The sweep runs every 15 s automatically; force one on demand:

```bash
curl -s -X POST localhost:8000/ops/resync
```

**Observed, healthy:**
```json
{"checkedAt":"2026-08-06T18:00:50Z","replicationLagBytes":0,"drift":{},"cacheEntriesEvicted":0,"inSync":true}
```

**Now break synchronization and watch it be detected:**

```bash
docker compose stop postgres-replica
curl -s -X POST localhost:8000/ops/resync
```

**Observed:** `{"replicationLagBytes":null,"drift":{},"cacheEntriesEvicted":0,"inSync":false}`
— the standby is gone and the sweep says so.

**Then let it recover.** Write data while the replica is down, bring it back,
and confirm the standby catches up:

```bash
docker compose start postgres-replica
sleep 15
curl -s -X POST localhost:8000/ops/resync
docker exec oms-postgres-primary psql -U oms -d oms -tAc "SELECT count(*) FROM customers;"
docker exec oms-postgres-replica psql -U oms -d oms -tAc "SELECT count(*) FROM customers;"
```

**Observed:** `inSync:true` with `replicationLagBytes:0`, and both nodes report
`3` — including the rows written while the standby was offline.

---

## NFR 2.4 — Transactions

**Atomicity across entities.** Issuing an invoice writes the invoice, stamps
`order.invoice_ref`, and advances the order — all or nothing:

```bash
INV=$(curl -s -X POST localhost:8000/api/v1/invoices -H 'Content-Type: application/json' \
  -d "{\"orderRef\":\"$ORDER\"}" | jq -r .id)
curl -s localhost:8000/api/v1/orders/$ORDER | jq '{status, invoiceRef}'
```

**Observed:** `{"status":"INVOICED","invoiceRef":"<the id just created>"}` — both
effects landed together.

**Isolation.** Two concurrent accepts on the same order: exactly one wins.

```bash
python -m pytest tests/test_transactions.py -v
```

The test drives 8 simultaneous `/accept` calls and asserts exactly one 200 and
seven 409s.

**Rollback.** A payment whose amount does not match the invoice total is
rejected, and no payment row is left behind:

```bash
curl -s -X POST localhost:8000/api/v1/payments -H 'Content-Type: application/json' \
  -d "{\"orderRef\":\"$ORDER\",\"amount\":\"1.00\",\"method\":\"CREDIT_CARD\"}"
docker exec oms-postgres-primary psql -U oms -d oms -tAc \
  "SELECT count(*) FROM payments WHERE order_ref='$ORDER';"
```

**Observed:** 400 with an `expected`/`received` detail, and a payment count
unchanged by the failed attempt.

---

## Full regression suite

```bash
pip install -r requirements.txt
python -m pytest tests/ -v
```

Covers the 7-step workflow, all state-machine guards, the 400/404/409 id
contract for every entity, the Field Constraint Table boundaries (BVA/EP), and
transaction isolation.
