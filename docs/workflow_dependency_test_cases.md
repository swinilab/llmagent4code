# Test Case Dependency on `workflow_apis.json`

This is a **derived view** of the full BVA/EP suite (`docs/OMS_TestCases_BVA_EP_EN.md`
/ `.xlsx`), not a replacement for it. The full suite stays the source of truth for
every run where `workflow_apis.json` is present and correct. This file exists to
answer one question: *when an app has no `workflow_apis.json` (or it declares no
`acceptOrder`-equivalent step), which test cases in the same suite still produce a
meaningful pass/fail signal?*

Two suite variants are meant to coexist, not to replace one another:
- **Full suite** — all test cases below, run when `workflow_apis.json` resolves an
  `acceptOrder`-equivalent step (`validator.expect_workflow_manifest: true` and the
  file is actually present/valid).
- **Without-workflow suite** — only the rows marked **Unaffected** below. Use this
  subset (or at least discount the others) when scoring an app whose prompt version
  never required `workflow_apis.json` (see `prompts/latest.md`), so missing ACCEPTED/
  INVOICED seed data doesn't get misread as an app defect.

Root cause and mechanics: [seed_context.py](../method_pipeline_v2/validators/tests/seed_context.py#L364-L371).
When no `acceptOrder`-equivalent step is found, `_provision()` returns early, so
`order_accepted_id`, `order_invoiced_id`, `invoice_id`, `bulk_invoiced_orders`, and
`bulk_accepted_order_ids` all stay empty/`None`. `order_placed_id` (order #1) is
unaffected — it is created before that lookup.

## Status legend

| Status | Meaning |
|---|---|
| Unaffected | Does not read any ACCEPTED/INVOICED/invoice seed id — result reflects the app's actual behavior regardless of `workflow_apis.json`. |
| Always-fail | Code path explicitly returns `result=False` (`_seed_unavailable`) or sends a placeholder string (e.g. `"<seed: order status=ACCEPTED>"`) as an id — deterministically fails, not a signal about the app. |
| Likely-fail (409→400 mismatch) | Expects `409` from an app operating on a real but wrong-state order; instead receives a malformed-id placeholder and most likely gets `400` — fails, but not for the reason the case claims to test. |
| False-positive risk | Expects `400` anyway (an invalid-field case); the broken placeholder `orderRef` may also independently cause `400`, so the case can "pass" without actually exercising the field it's named for. |

## Customer (50 cases) — all Unaffected

`TC_CUS_ID_01..04`, `TC_CUS_NAME_01..10`, `TC_CUS_ADDRESS_01..07`,
`TC_CUS_PHONE_01..08`, `TC_CUS_BANKACCTNU_01..06`, `TC_CUS_BANKNAME_01..06`,
`TC_CUS_ROLE_01..06`, `TC_CUS_ORDERHIST_01..03`.

No dependency on Order/Invoice/Payment state anywhere in `CustomerTestGroup.py`.

## Product (25 cases) — all Unaffected

`TC_PRO_ID_01..03`, `TC_PRO_DESCRIPTIO_01..07`, `TC_PRO_PRICEAMT_01..08`,
`TC_PRO_CURRENCY_01..07`.

No dependency on Order/Invoice/Payment state anywhere in `ProductTestGroup.py`.

## Order (28 cases)

| Test Case | Status | Reason |
|---|---|---|
| TC_ORD_CUSTREF_01..04 | Unaffected | customer-only |
| TC_ORD_LINEITEMS_01..07 | Unaffected | product-only |
| TC_ORD_QTY_01..07 | Unaffected | product-only |
| TC_ORD_UNITPRICE_01..02 | Unaffected | product-only |
| TC_ORD_TOTALAMT_01..02 | Unaffected | server-computed on creation, no lifecycle needed |
| TC_ORD_STATUS_01..03 | Unaffected | checks default/rejected status on creation, not a transition |
| TC_ORD_INVREF_01 | Unaffected | uses `seed_order_placed_id` (order #1, always seeded) |
| **TC_ORD_INVREF_02** | **Always-fail** | uses `seed_order_with_invoice_id` = `seed.order_invoiced_id`; `None` when workflow missing → falls back to placeholder `"<seed: order status=ACCEPTED, invoiceRef set>"` sent as `{id}` in a GET → expects `200`, gets `400`/`404` on the malformed id |
| TC_ORD_INVREF_03 | Unaffected | targets a hardcoded not-found UUID, no seed involved |

## Payment (18 cases)

| Test Case | Status | Reason |
|---|---|---|
| TC_PAY_ORDERREF_01 | **Always-fail** | `_next_invoiced_order()` → `None`, bulk queue empty |
| TC_PAY_ORDERREF_02 | Unaffected | uses `seed_order_placed_id` (real order #1) |
| TC_PAY_ORDERREF_03 | Unaffected | hardcoded not-found UUID |
| TC_PAY_ORDERREF_04 | Unaffected | hardcoded malformed string |
| TC_PAY_AMOUNT_01 | **Always-fail** | needs dedicated INVOICED order, queue empty |
| TC_PAY_AMOUNT_02 | **Likely-fail** | expects `409`; default `orderRef` placeholder → likely `400` |
| TC_PAY_AMOUNT_03 | **Likely-fail** | same as above |
| TC_PAY_AMOUNT_04 | False-positive risk | expects `400` (amount=0) anyway |
| TC_PAY_AMOUNT_05 | False-positive risk | expects `400` (negative amount) anyway |
| TC_PAY_AMOUNT_06 | False-positive risk | expects `400` (null amount) anyway |
| TC_PAY_STATUS_01 | **Always-fail** | needs dedicated INVOICED order, queue empty |
| TC_PAY_STATUS_02 | False-positive risk | expects `400` (client-set status) anyway |
| TC_PAY_STATUS_03 | False-positive risk | expects `400` (unknown enum) anyway |
| TC_PAY_METHOD_01 | **Always-fail** | needs dedicated INVOICED order, queue empty |
| TC_PAY_METHOD_02 | **Always-fail** | needs dedicated INVOICED order, queue empty |
| TC_PAY_METHOD_03 | **Always-fail** | needs dedicated INVOICED order, queue empty |
| TC_PAY_METHOD_04 | False-positive risk | expects `400` (unknown enum) anyway |
| TC_PAY_METHOD_05 | False-positive risk | expects `400` (null method) anyway |

## Invoice (26 cases)

| Test Case | Status | Reason |
|---|---|---|
| TC_INV_ORDERREF_01 | **Always-fail** | `_next_accepted_order()` → `None`, bulk queue empty |
| TC_INV_ORDERREF_02 | Unaffected | uses `seed_order_placed_id` (real order #1) |
| TC_INV_ORDERREF_03 | Unaffected | hardcoded not-found UUID |
| TC_INV_ORDERREF_04 | Unaffected | hardcoded malformed string |
| TC_INV_BILLNAME_01..04 | False-positive risk | expect `400` (rejected billingInfo) anyway |
| TC_INV_TOTALAMT_01 | **Always-fail** | needs dedicated ACCEPTED order, queue empty |
| TC_INV_TOTALAMT_02..03 | False-positive risk | expect `400` anyway |
| TC_INV_ISSUEDATE_01 | **Always-fail** | needs dedicated ACCEPTED order, queue empty |
| TC_INV_ISSUEDATE_02..07 | False-positive risk | expect `400` anyway |
| TC_INV_DUEDATE_01 | **Always-fail** | needs dedicated ACCEPTED order, queue empty |
| TC_INV_DUEDATE_02 | **Always-fail** | needs dedicated ACCEPTED order, queue empty |
| TC_INV_DUEDATE_03..05 | False-positive risk | expect `400` anyway |
| TC_INV_STATUS_01 | **Always-fail** | needs dedicated ACCEPTED order, queue empty |
| TC_INV_STATUS_02..03 | False-positive risk | expect `400` anyway |

## Summary

| Entity | Total | Unaffected | Always-fail | Likely-fail | False-positive risk |
|---|---|---|---|---|---|
| Customer | 50 | 50 | 0 | 0 | 0 |
| Product | 25 | 25 | 0 | 0 | 0 |
| Order | 28 | 27 | 1 | 0 | 0 |
| Payment | 18 | 3 | 6 | 2 | 7 |
| Invoice | 26 | 3 | 6 | 0 | 17 |
| **Total** | **147** | **108** | **13** | **2** | **24** |

**Reading this table for scoring:** the 108 *Unaffected* rows are the safe
"without-workflow" subset — a real signal about the app either way. The 13
*Always-fail* + 2 *Likely-fail* rows should be excluded from pass-rate scoring
entirely when `workflow_apis.json` is absent by design (not reported as app
defects). The 24 *False-positive risk* rows can still be counted, but a `pass`
there is weaker evidence than usual — it may only mean the broken `orderRef`
happened to also trigger `400`.
