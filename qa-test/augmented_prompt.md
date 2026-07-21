# Task Prompt

## Objective

For each tactic specified in the target prompt below, find the **top-5 libraries** that support that tactic. Pull the documentation for each library and provide a code sample demonstrating usage of the tactic (e.g., `import x, y` and call `x`). Save each code example as well-documented, easy-to-read, segmented text.

## Output Contract (STRICT)

Generate **only** what is explicitly required below. Do not add preamble, summaries, closing remarks, meta-commentary, or any content not specified here.

Produce exactly the following artifacts:

1. **`tactics.csv`** — the tactics mapping only. This is the primary deliverable.
   - One row per tactic × library pairing (5 libraries per tactic).
   - Columns: `nfr_id`, `nfr_name`, `architectural_mechanism`, `module_component`, `verification_method`, `library`, `library_rank`, `code_sample`.
   - The `code_sample` cell must contain the well-documented, segmented usage example for that library (escape/quote as needed for valid CSV).
   - Nothing else belongs in this file — no headers beyond the column row, no notes, no explanations.

2. **`reasoning.md`** — all reasoning, analysis, library-selection justification, trade-off discussion, and any chain-of-thought. Everything that is *not* a raw tactic entry goes here and **only** here.

### Rules

- The tactics file (`tactics.csv`) must contain the tactics **and nothing else**. If content is explanatory, it belongs in `reasoning.md`.
- Do not duplicate reasoning into the CSV or tactics into the reasoning file.
- Do not print anything to stdout beyond a one-line confirmation of the two files written (e.g. `Wrote tactics.csv (N rows), reasoning.md`).
- Output only the two files. No third file, no inline dump of the full content in the response body.

## NFR Traceability Matrix (MANDATORY)

Before writing any code, produce (inside `tactics.csv`) the mapping of every NFR below to:
- The **architectural mechanism** used to satisfy it.
- The **module/component** where it lives.
- A one-line **verification method** (how a reviewer would confirm it works).

## Non-Functional Requirements to satisfy

- **NFR 1.1 — Response Time:** Core journeys (product search, cart, checkout) must minimize round-trip latency under load.
- **NFR 1.2 — Concurrency & Resource Utilization:** System must exploit available server resources with minimal queuing.
- **NFR 1.3 — Queue Management:** Sudden spikes must not crash the system.
- **NFR 2.1 — Graceful Degradation:** Under extreme resource contention, the system must degrade non-essential features to ensure core checkout functionality remains available.
- **NFR 2.2 — Fault Detection and Recovery:** The application must detect internal component failures and automatically attempt to recover or reconnect, minimizing user-facing errors.
- **NFR 2.3 — State Preservation:** In the event of an unexpected application process crash, the system must be able to restore its operational state and resume processing pending orders upon restart with minimal data loss.