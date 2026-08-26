# Test Case / Validator Changes Log

Tracks corrections made to the OMS test case suite (`docs/OMS_TestCases_BVA_EP_EN.xlsx`
/ `.md`) and the corresponding functional test harness code
(`method_pipeline_v2/validators/tests/test_groups/`), so later review knows
*why* an expected value or test body changed and can re-check the reasoning.

---

## 2026-08-27 — Accept 422 alongside 400 for POST body-validation test cases

**Files:** `method_pipeline_v2/interfaces/base.py`,
`method_pipeline_v2/validators/tests/test_groups/CustomerTestGroup.py`,
`method_pipeline_v2/validators/tests/test_groups/ProductTestGroup.py`,
`method_pipeline_v2/validators/tests/test_groups/OrderTestGroup.py`,
`method_pipeline_v2/validators/tests/test_groups/PaymentTestGroup.py`,
`method_pipeline_v2/validators/tests/test_groups/InvoiceTestGroup.py`.

**What changed:**
- `ITestGroup._check()` gained an optional `acceptable: tuple[int, ...] | None`
  parameter. When given, `actual_status in acceptable` also counts as a pass,
  in addition to the exact `expected_status` match; the reported
  `expected_status` in `TestResult`/the JSON report is unchanged either way.
- Every test-case method across the five groups whose flow is
  `self._post(body)` followed by `self._check(<id>, 400, ...)` — i.e. a POST
  body-validation case (field length/format/enum/type violations) — now
  passes `acceptable=(400, 422)`. 83 test-case call sites were updated this
  way (28 Customer, 14 Product, 15 Order, 8 Payment, 18 Invoice).
- Left untouched: GET path-param cases expecting 400 for a malformed id
  (`TC_CUS_ID_03`, `TC_PRO_ID_03` — these already get 400 from the apps'
  custom UUID-parsing handler, not from Pydantic body validation), and every
  case expecting 200/201/404/405/409. Cases currently failing with a real
  `500 ProgrammingError` app bug still fail — this change only forgives the
  400-vs-422 status-code mismatch, it does not accept 500.

**Why:** FastAPI/Pydantic returns `422 Unprocessable Entity` by default for
request-body validation errors, not `400 Bad Request`; the BVA/EP suite
(`docs/OMS_TestCases_BVA_EP_EN.xlsx`) was written expecting `400` for these
cases. That is a framework-convention mismatch, not a defect in the
generated app's validation logic (the app *does* reject the bad input with a
correct error body — see `functional_test_report_20260827_002723.json`,
where e.g. `TC_CUS_NAME_01` returns `422` with the exact expected validation
message). Requested by the user after reviewing that report, scoped
explicitly to "these test cases, not all" so the 500-status failures (a
separate, real backend bug — see the `ProgrammingError` seed warning in the
same report) keep failing and aren't masked by this change.

---

## 2026-08-26 — Verify computed values in TC_ORD_TOTALAMT_01 / TC_ORD_UNITPRICE_01 instead of status-only

**Files:** `method_pipeline_v2/validators/tests/test_groups/OrderTestGroup.py`,
`method_pipeline_v2/validators/tests/seed_context.py`,
`method_pipeline_v2/validators/FunctionalValidator.py`.

**What changed:**
- `SeedContext` gained `product_price: str | None`. `seed_context.py`'s
  `_provision()` now captures it from the seeded product's own creation
  response (`resp["price"]["amount"]`, falling back to the sent value if the
  app doesn't echo it) right after `ctx.product_id` is set.
  `FunctionalValidator` passes it into `OrderTestGroup` as
  `seed_product_price`.
- `OrderTestGroup.__init__` gained `seed_product_price` (falls back to
  `DEFAULT_PRODUCT_PRICE = "10.00"`, matching `ProductTestGroup`'s own
  hardcoded default, for parity with the existing `NEEDS_SEED_*`/`DEFAULT_*`
  fallback pattern used elsewhere in this file and in Payment/Invoice).
- `tc_ord_unitprice_01` now compares `resp["lineItems"][0]["unitPriceSnapshot"]`
  against `seed_product_price` (via `Decimal`, so `"10.0"` vs `"10.00"`
  formatting differences don't cause a false failure) and flips `result.result`
  to `False` on a mismatch, instead of accepting any `201`.
- `tc_ord_totalamt_01` now compares `resp["totalAmount"]` against
  `Decimal(seed_product_price) * 1` (the standard body's single line item,
  quantity 1) the same way.

**Why:** both cases' docstrings claimed to verify a server-computed value
("server correctly computes total", "server derives snapshot from current
Product price") but only asserted `status == 201` — an app that accepted the
order while silently miscomputing/omitting the price would still report a
pass. `TC_INV_TOTALAMT_01` already verifies its analogous value
(`InvoiceTestGroup.py` `tc_inv_totalamt_01`), so this brings the two Order
cases in line with that existing precedent rather than leaving them as an
unexplained gap. See the `code-review`-style audit earlier the same day
(chat, not a file) that first surfaced this as a false-positive risk
alongside the already-documented `docs/workflow_dependency_test_cases.md`
cases; those seed-ambiguity cases are left as-is per that discussion (the
fix there is to remove the ambiguous seed data, not to add response
assertions - not done in this change).

---

## 2026-08-26 — Isolate workflow-independent test cases; add `validator.expect_workflow_manifest`

**Files:** `docs/workflow_dependency_test_cases.md` (new),
`method_pipeline_v2/validators/FunctionalValidator.py`.
(Pipeline config changes themselves — `pipeline_config.yaml`,
`pipeline_config.yaml.example` — are not logged here per convention; see the
files directly.)

**What changed:**
- New `docs/workflow_dependency_test_cases.md`: a derived table over the
  existing BVA/EP suite (`docs/OMS_TestCases_BVA_EP_EN.md`/`.xlsx`, left
  untouched) classifying every one of the 147 Customer/Product/Order/Payment/
  Invoice test cases as `Unaffected`, `Always-fail`, `Likely-fail`, or
  `False-positive risk` with respect to a missing/absent `workflow_apis.json`.
  108 cases are Unaffected; 13 always fail via the explicit
  `_seed_unavailable(...)` path (or an equivalent malformed-placeholder GET
  for `TC_ORD_INVREF_02`) regardless of app correctness; 2 fail via a
  409→400 mismatch; 24 carry a false-positive risk (they expect 400 anyway,
  so a broken seed `orderRef` can make them pass without exercising the
  field they're named for). The two suite variants — full and
  without-workflow — are meant to coexist: the full suite (unchanged) is
  authoritative whenever `workflow_apis.json` resolves an acceptOrder step;
  the without-workflow subset is the `Unaffected` rows only.
- `FunctionalValidator.py`: reads the new `validator.expect_workflow_manifest`
  config flag. Missing `workflow_apis.json` is now logged distinctly
  depending on it — as a generation defect when `true` (default), or as
  expected-for-this-prompt-version when `false` — and both booleans
  (`workflow_manifest_present`, `workflow_manifest_expected`) are now written
  into `ValidationResult.details` for the functional stage. Seeding
  mechanics in `seed_context.py` are unchanged; this only changes how the
  absence is logged/reported, not what gets seeded.

**Why:** `prompts/latest.md` (used for some already-generated apps, e.g.
`claude-latest-fixed-compile`) never asked for `workflow_apis.json` — only
`prompts/latest_dynamic.md` added that requirement. Scoring those older apps
against evaluator checks that assume the newer prompt's manifest wrongly
counts a prompt-version gap as an app defect, and silently drags down the
pass rate of ~26% of the suite (39/147) for a reason unrelated to code
quality. The new doc lets a reviewer separate "app is broken" from "this
app's prompt never asked for this file" without re-deriving the seeding
mechanics each time; the config flag makes that distinction explicit per run
instead of implicit in whether the file happens to exist.

---

## 2026-08-26 — Stop falling back to the shared order when the bulk seed queue runs short (Payment/Invoice)

**Files:** `method_pipeline_v2/validators/tests/test_groups/PaymentTestGroup.py`,
`method_pipeline_v2/validators/tests/test_groups/InvoiceTestGroup.py`,
`method_pipeline_v2/report_writer.py`

**What changed:**
- `PaymentTestGroup._next_invoiced_order()` and
  `InvoiceTestGroup._next_accepted_order()` now return `None` when their
  bulk queue is exhausted, instead of silently falling back to the single
  shared `seed_order_invoiced_id` / `seed_order_accepted_id`.
- Both classes gained `_seed_unavailable(testcase_id, expected_status)`,
  which builds a `TestResult` with `result=False`,
  `response_body="seed data unavailable: ..."` and no HTTP call made.
- The 6 happy-path methods in each class (`tc_pay_orderref_01`/`amount_01`/
  `status_01`/`method_01..03`; `tc_inv_orderref_01`/`totalamt_01`/
  `issuedate_01`/`duedate_01..02`/`status_01`) now check for `None` first
  and return `_seed_unavailable(...)` instead of firing a request.
- `report_writer.py`: the pipeline's `.txt` report now also prints
  `seed context log : <path>` next to the existing `full report : <path>`
  line for the functional stage, so the seed log referenced by these new
  "seed data unavailable" messages is easy to find from the top-level
  report. (`FunctionalValidator` already produced `seed_log_path` in its
  `ValidationResult.details`; report_writer just wasn't printing it.)

**Why (fragile-1 from the pre-fix audit):** the 6-happy-path bulk queues
added for Payment and Invoice are sized to exactly match their 6 consumers,
so today (bulk seeding fully succeeding) the shared single order is never
touched by happy-path tests and this path never triggers. But the old
fallback silently reused `seed_order_invoiced_id`/`seed_order_accepted_id`
if the queue ever ran short - and that exact order is also relied on by the
negative-path tests (`TC_PAY_AMOUNT_02..06`, `STATUS_02/03`, `METHOD_04/05`,
`ORDERREF_02`; `TC_INV_ORDERREF_02`) to stay in a known, untouched state.
A happy-path test silently consuming it (paying it / invoicing it) would
have corrupted those negative-path tests' results too, in a way that would
look like an unrelated app regression rather than a seed shortfall. Failing
loudly and specifically for just the starved test(s) - while leaving the
shared order alone for the tests that actually depend on it - is safer than
a fallback that trades one clear failure for several confusing ones.

**Not itself a currently-observed bug:** `functional_test_report_20260826_012040.json`
shows 0 seed warnings and both bulk queues fully seeded (6/6 each), so this
fallback path has not fired in any run so far - this is a preventive fix
for the scenario, not a fix for an existing wrong result.

---

## 2026-08-26 — Seed 6 dedicated ACCEPTED orders for Invoice happy-path tests

**Files:** `method_pipeline_v2/validators/tests/seed_context.py`,
`method_pipeline_v2/validators/FunctionalValidator.py`,
`method_pipeline_v2/validators/tests/test_groups/InvoiceTestGroup.py`

**What changed:** `SeedContext` gained `bulk_accepted_order_ids: list[str]`.
`seed_context.py` refactored the create+accept steps out of
`_provision_invoiced_order()` into a new `_provision_accepted_order()`
helper (shared by both), then `_provision()` calls it
`INVOICE_HAPPY_PATH_ORDER_COUNT = 6` more times after the Payment bulk
queue, best-effort. `FunctionalValidator` passes
`seed.bulk_accepted_order_ids` into `InvoiceTestGroup` as
`seed_bulk_accepted_order_ids`. `InvoiceTestGroup` gained
`_next_accepted_order()`, which pops one dedicated order id per call;
`tc_inv_orderref_01`, `tc_inv_totalamt_01`, `tc_inv_issuedate_01`,
`tc_inv_duedate_01/02`, and `tc_inv_status_01` (the 6 happy-path invoice
cases, each expecting `201`) now each pull their own order via this instead
of all sharing `seed_order_accepted_id`. Falls back to the shared order if
the bulk queue is exhausted/unavailable, same pattern as the Payment and
LINEITEMS bulk fixes.

**Why:** `functional_test_report_20260826_011325.json` showed all 6 of
these failing with `409` ("order must be ACCEPTED before invoicing",
`orderStatus: INVOICED`) - including `TC_INV_ORDERREF_01`, the *first* test
in the group to run. Creating an invoice is a one-time `ACCEPTED ->
INVOICED` transition, same class of bug as the Payment fix above,
compounded here: `seed_order_accepted_id` (`ctx.order_accepted_id`) is the
*same* main lifecycle order that `_provision()` already invoices during
seeding itself (to produce `order_invoiced_id`/`invoice_total_amount` for
`PaymentTestGroup`), so by the time `InvoiceTestGroup` ran even its first
test, that order's status was already `INVOICED`, not `ACCEPTED` - every
happy-path test was guaranteed to fail, not just the ones after the first.
The app's `409` was correct throughout. Test-harness/seed defect, not an
app defect. **App code was not touched.**

**Not in scope / known related gap:** same caveat as the Payment fix -
negative-path invoice tests (`TC_INV_ORDERREF_02`, etc.) still target the
shared `seed_order_placed_id`/`seed_order_accepted_id`; they weren't
reported as failing so were left alone, but a fully rigorous fix would give
them dedicated fixtures too.

---

## 2026-08-26 — InvoiceTestGroup: stop sending billingInfo by default; TC_INV_BILLNAME_02/03 expected status 201 → 400

**Files:** `docs/OMS_TestCases_BVA_EP_EN.xlsx` (Invoice sheet), `docs/OMS_TestCases_BVA_EP_EN.md`,
`method_pipeline_v2/validators/tests/test_groups/InvoiceTestGroup.py`,
`method_pipeline_v2/validators/tests/seed_context.py`

**What changed:**
- `InvoiceTestGroup.standard_request_body` no longer includes `billingInfo`
  by default (only `orderRef`, `issueDate`, `dueDate`).
- `tc_inv_billname_01..04` now each add `body["billingInfo"] = {"name": ...}`
  explicitly instead of mutating a shared default. `TC_INV_BILLNAME_02`
  (BC-Min, 2 chars) and `TC_INV_BILLNAME_03` (BC-Max, 100 chars) changed
  expected status `201 → 400` (all 4 BILLNAME cases now expect `400`).
- `seed_context.py`: removed the now-dead "retry invoice creation without
  billingInfo on 400" fallback in both `_provision()` and
  `_provision_invoiced_order()`, since the first attempt no longer sends
  billingInfo at all.

**Why:** `functional_test_report_20260826_010121.json` showed 10 Invoice
test cases failing, all with the identical app error
`{"field": "billingInfo", "error": "Extra inputs are not permitted"}` -
including tests completely unrelated to billingInfo
(`TC_INV_ORDERREF_01/02/03`, `TC_INV_TOTALAMT_01`, `TC_INV_ISSUEDATE_01`,
`TC_INV_DUEDATE_01/02`, `TC_INV_STATUS_01`). The workbook's own Remarks
column already says billingInfo is a "Snapshot of Customer.name" - the same
"copied at issue time" wording the domain spec
(`method_pipeline_v2/prompts/latest.md:146-147`) uses, the same category as
`Customer.orderHistory` (read-only/server-derived; see the
TC_CUS_ORDERHIST_01 entry above). `seed_context.py` had already worked
around this exact behavior with a "retry without billingInfo" fallback,
proving it was a known but unapplied fix - `InvoiceTestGroup` itself never
got the same treatment, so 10/26 Invoice tests collaterally failed on a
field they weren't testing.

**Root cause:** test-harness/validator defect, not an app defect - same
category as TC_CUS_ORDERHIST_01. Fixing it (dropping billingInfo from the
shared body) resolves the 8 unrelated collateral failures
(ORDERREF_01/02/03, TOTALAMT_01, ISSUEDATE_01, DUEDATE_01/02, STATUS_01) for
free. `TC_INV_BILLNAME_01` and `TC_INV_BILLNAME_04` were already returning
`400` before this fix but for the wrong reason (rejected as an extra field,
not for violating the 2-100 char length boundary they were designed to
isolate) - same false-positive-pass pattern as TC_ORD_LINEITEMS_04 before
its fix. Since billingInfo can never be validly client-supplied, there is
no length boundary left to test via this endpoint, so `TC_INV_BILLNAME_02`
and `_03` (previously expecting `201` as the "valid" boundary cases) are
changed to `400` for consistency with `_01`/`_04` and with the read-only
rule, rather than kept as an unreachable "valid" case.

---

## 2026-08-26 — Seed 6 dedicated INVOICED orders for Payment happy-path tests

**Files:** `method_pipeline_v2/validators/tests/seed_context.py`,
`method_pipeline_v2/validators/FunctionalValidator.py`,
`method_pipeline_v2/validators/tests/test_groups/PaymentTestGroup.py`

**What changed:** `SeedContext` gained `bulk_invoiced_orders: list[dict]`
(`{order_id, invoice_id, invoice_total_amount}`); `_provision()` now walks
`PAYMENT_HAPPY_PATH_ORDER_COUNT = 6` additional orders through
PLACED → ACCEPTED → INVOICED (via the new `_provision_invoiced_order()`
helper, best-effort - stops and warns if the app starts failing partway
through). `FunctionalValidator` passes `seed.bulk_invoiced_orders` into
`PaymentTestGroup` as `seed_bulk_invoiced_orders`. `PaymentTestGroup` gained
`_next_invoiced_order()`, which pops one dedicated order/invoice-total pair
per call; `tc_pay_orderref_01`, `tc_pay_amount_01`, `tc_pay_status_01`, and
`tc_pay_method_01/02/03` (the 6 happy-path payment cases, each expecting
`201`) now each pull their own order via this instead of all sharing
`seed_order_invoiced_id`. Falls back to the shared single order if the bulk
queue is exhausted/unavailable, same defensive pattern as the LINEITEMS
bulk-product fix.

**Why:** `functional_test_report_20260826_004935.json` showed
`TC_PAY_AMOUNT_01`, `TC_PAY_STATUS_01`, and `TC_PAY_METHOD_01/02/03` failing
with `409` ("order is not in a payable state", `orderStatus: PAID`) instead
of expected `201`. Paying an order is a one-time `INVOICED -> PAID`
transition. All 6 happy-path payment test cases were built against the
single shared `seed_order_invoiced_id`; whichever ran first
(`TC_PAY_ORDERREF_01`) legitimately paid it and moved it to `PAID`, so every
later happy-path test hit the same already-paid order and correctly got
`409` from the app - the app's behavior was correct throughout. This was a
test-harness/seed defect (one shared order asked to be paid 6 times), not
an app defect. **App code was not touched.**

**Not in scope / known related gap:** the negative-path payment tests
(`TC_PAY_AMOUNT_02/03`, `TC_PAY_ORDERREF_02`, etc.) still target the shared
`seed_order_invoiced_id`/`seed_order_placed_id`. Once any happy-path test
consumes the shared order, a negative-path test still gets its expected
`409` - but only because the order is already `PAID`, not necessarily
because the app enforces the specific rule that test is meant to isolate
(e.g. amount-mismatch). This wasn't reported as failing (status code still
matches), so it was left alone per the request scope, but the same
"give-each-test-its-own-fixture" pattern would apply here for a fully
rigorous fix.

---

## 2026-08-26 — Seed 100 distinct products for TC_ORD_LINEITEMS_03 (BC-Max)

**Files:** `method_pipeline_v2/validators/tests/seed_context.py`,
`method_pipeline_v2/validators/FunctionalValidator.py`,
`method_pipeline_v2/validators/tests/test_groups/OrderTestGroup.py::tc_ord_lineitems_03`

**What changed:** `SeedContext` gained `bulk_product_ids: list[str]`;
`_provision()` now creates `BULK_PRODUCT_COUNT = 100` distinct products
(best-effort, stops and warns if the app starts failing partway through).
`FunctionalValidator` passes `seed.bulk_product_ids` into `OrderTestGroup` as
`seed_bulk_product_ids`. `tc_ord_lineitems_03` now builds its 100-item
`lineItems` array from these 100 distinct product ids instead of repeating
`seed_product_id` 100 times, falling back to the old repeat behavior only
for however many products seeding couldn't produce.

**Why:** `functional_test_report_20260826_003856.json` showed
TC_ORD_LINEITEMS_03 failing (`400` instead of expected `201`) while the
sibling TC_ORD_LINEITEMS_07 (duplicate-productRef rejection) passed —
meaning the app was correctly rejecting the *duplicated* productRef, not the
item count. The test was accidentally exercising the "no duplicate product"
rule instead of the "up to 100 items" boundary it's meant to test, exactly
as flagged by the docstring the test already carried
("here the same seed product id is repeated as a placeholder"). This was a
test-harness/seed defect, not an app defect.

**Update (2026-08-26):** TC_ORD_LINEITEMS_04 (101 items, BC-Max+1) fixed the
same way — it now builds its `lineItems` from `seed_bulk_product_ids[:100] +
[seed_product_id]` (101 distinct products; `seed_product_id` is the single
seed created before the bulk batch, so it's guaranteed distinct from every
id in `seed_bulk_product_ids`), instead of repeating `seed_product_id` 101
times. It happened to still return `400` before this fix, but for the wrong
reason (duplicate-productRef rejection, not the >100-item rejection the
case is meant to exercise) — same false-positive risk as LINEITEMS_03 had,
just masked because both paths return 400.

---

## 2026-08-26 — TC_CUS_ID_04: expected status 400 → 405

**Files:** `docs/OMS_TestCases_BVA_EP_EN.xlsx` (Customer sheet), `docs/OMS_TestCases_BVA_EP_EN.md`,
`method_pipeline_v2/validators/tests/test_groups/CustomerTestGroup.py::_tc_cus_id_04`

**What changed:** Expected HTTP status for "Empty/null id" (EC-Invalid-3) changed
from `400` to `405`.

**Why:** The test issues `GET {api}/customers/` (id="" → trailing slash, no id
segment). This URL matches the *collection* route (`POST /customers` to
create), not the get-by-id handler — so the "id is required" validation logic
inside the id-path handler is never reached. A REST-conventional server
returns `405 Method Not Allowed` for a GET on a POST-only collection route,
not a `400`. The `400` in the original workbook was a REST-convention
*default* that wasn't reconciled against how the harness actually builds the
URL (see workbook README: "Expected HTTP Status values are REST-convention
defaults and must be reconciled with the actual API error contract").

**Caveat:** 405 assumes the app's collection route only supports POST (no
GET-list). If a generated app *does* implement `GET /customers` as list-all,
this test would legitimately see 200 instead — that's a property of the app,
not something this test can control, since the harness never guesses
undeclared routes.

---

## 2026-08-26 — TC_CUS_PHONE_07: reviewed, no change (confirmed correct as-is)

**File:** `method_pipeline_v2/validators/tests/test_groups/CustomerTestGroup.py::_tc_cus_phone_07`

**What changed:** Docstring only — clarified rationale. Input value (`+8401234567`)
and expected status (`400`) are unchanged.

**Why raised:** `functional_test_report_20260826_001725.json` shows the app
under test returned `201` (accepted) instead of the expected `400` for this
input, which looked like it might be a bad test case (same category of bug as
TC_CUS_ID_04 above).

**Why no change:** The domain rule is "must not start with 0 after country
code" (`method_pipeline_v2/prompts/latest.md` etc.). A raw VN mobile number
like `0901234567` converts to E.164 as `+84901234567` — the country code
`84` already stands in for the local trunk `0`. Keeping the local `0` after
`+84` (`+8401234567`) is the classic conversion mistake and is invalid by
convention even though it's a single literal `0` character — it does not
need two literal `0`s to be invalid.

**Root cause of the 201:** app-side validation gap. The value satisfies the
base E.164 regex `^\+?[1-9]\d{7,14}$` (first digit after `+` is `8`, length
10 is in [8,15]) — that regex alone cannot express "no 0 right after the
country code" since it doesn't know the country code's digit length. The
generated app almost certainly only implements the base regex and skips the
extra semantic rule. This is a real app defect, not a test-harness defect —
left as `400`/unchanged.

**Confirmed recurring app defect (2026-08-26, `functional_test_report_20260826_003856.json`):**
same `201` (should be `400`) reproduced against `claude-latest copy`
(`code: C:\Users\Admin\Documents\GitHub\llmagent4code\claude-latest copy`),
a completely different generated app from the chatdev-qwen35 one that
originally surfaced this. Confirms the test case and its `400` expectation
are correct — multiple independently generated apps only implement the base
E.164 regex and skip the "no 0 right after country code" semantic rule, so
this is a systemic gap in how the domain spec's phone rule gets implemented,
not a one-off app bug or a test-harness bug.

---

## 2026-08-26 — TC_CUS_ORDERHIST_01: expected status 201 → 400

**Files:** `docs/OMS_TestCases_BVA_EP_EN.xlsx` (Customer sheet), `docs/OMS_TestCases_BVA_EP_EN.md`,
`method_pipeline_v2/validators/tests/test_groups/CustomerTestGroup.py::_tc_cus_orderhist_01`

**What changed:** Expected HTTP status for "Empty array" (EC-Valid-1) changed
from `201` to `400`. Expected Output text updated to
"Rejected - orderHistory is read-only/server-derived, extra field not
permitted".

**Why:** `orderHistory` is documented as read-only/server-derived in this
same row's own Remarks column — the same remark carried by
TC_CUS_ORDERHIST_02 and TC_CUS_ORDERHIST_03, both of which correctly expect
`400` when the client supplies this field. TC_CUS_ORDERHIST_01 contradicted
that by expecting `201` for `orderHistory: []`, treating an empty array as
an acceptable value rather than as "client is setting a read-only field."
A strict extra-fields-forbidden schema (which is what
`functional_test_report_20260826_001725.json` showed the app under test
actually enforcing — `"Extra inputs are not permitted"` for `orderHistory`)
rejects the field regardless of its value, so `400` is the behavior
consistent with the field's own read-only constraint and with its sibling
test cases. The app's `201`-expecting failure here was a test-case defect,
not an app defect.
