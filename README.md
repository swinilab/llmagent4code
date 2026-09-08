# LLMAgent4Code: Architecture-Driven Evaluation of LLM-Based Coding Agents 🏛️

[![Tech Report](http://img.shields.io/badge/Tech_Report-Architecture_Driven-99D4C8.svg)](https://drive.google.com/file/d/14LbqCPxYrkw3Q2xwxmNWQURzb3qXWjV2)
[![Case Study](https://img.shields.io/badge/Case_Study-OrderMan-E3E4C8.svg)](#case-study-orderman)
[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)

This repository is the replication package for an empirical study that evaluates
LLM-based coding agents **beyond executability and functional correctness**, by
asking whether a generated system realizes the architecture it was asked to
build.

Quality-attribute requirements are stated to the agent as **named architectural
tactics**. A tactic must be realized through an implementation mechanism, so it
leaves observable source-level evidence. The pipeline measures that evidence
directly: **tactic conformance** asks whether each requested mechanism is
corroborated at the location the agent itself claims, and the **Tactic
Interaction Conflict Score (TICS)** localizes where implementations of
potentially conflicting tactics meet in the recovered function graph.

> **Paper**: *Towards Architecture-Driven Code Generation with LLM-based Coding
> Agent: An Empirical Study* — Cong Van Nguyen, Duc Minh Le, Manh Duc Nguyen,
> Khue Minh Hoang.

## Table of Contents

- [Overview](#overview)
- [Pipeline](#pipeline)
- [Evaluation Metrics](#evaluation-metrics)
  - [Tactic conformance](#tactic-conformance-rq2)
  - [Architectural interaction](#architectural-interaction-rq3)
  - [Conflict model](#conflict-model)
- [Results](#results)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Experiment Workflow](#experiment-workflow)
  - [Step 1 — Configure a Run](#step-1--configure-a-run)
  - [Step 2 — Generate an Application](#step-2--generate-an-application)
  - [Step 3 — Run the Dynamic Stages](#step-3--run-the-dynamic-stages)
  - [Step 4 — Run the Static Stages](#step-4--run-the-static-stages)
  - [Step 5 — Read the Reports](#step-5--read-the-reports)
- [Repository Structure](#repository-structure)
- [Case Study: OrderMan](#case-study-orderman)
- [Corpus](#corpus)
- [Reproducing the Paper's Tables](#reproducing-the-papers-tables)
- [Development](#development)
- [Citation](#citation)

## Overview ⭐

A generated system that starts, answers a health probe and publishes the
required routes can still be 1.4% functionally correct — and a system that
passes 98% of its functional suite can still leave half of its declared
architectural mechanisms uncorroborated in code. These are different
properties, so this pipeline measures them separately across five stages:

| Stage | Question | RQ | Kind |
|---|---|---|---|
| **Executability** | Does it build, start and answer a health probe? | RQ1 | dynamic |
| **Functional correctness** | Do the 147 field-constraint cases pass? | RQ1 | dynamic |
| **Workflow integration** | Do the 19 lifecycle checks pass? | RQ1 | dynamic |
| **Tactic conformance** | Is each claimed tactic corroborated at its claimed location? | RQ2 | static |
| **Conflict exposure (TICS)** | Where do conflicting tactic realizations meet? | RQ3 | static |

**Key features:**

- **Tactics as the unit of architectural evaluation** — six Bass–Clements–Kazman
  tactics (two performance, four availability) are requested by the prompt
  without prescribing language, framework, or mechanism, so implementation
  choices remain experimental outcomes.
- **Agent-declared traces, independently verified** — each agent emits
  `nfr-trace.json` mapping every tactic to `path::qualified_name` functions. The
  trace is treated as a *declaration*, never as ground truth: the analyzer checks
  whether the function exists, is non-trivial, and reaches the library the trace
  claims for it.
- **Manifest-driven test harness** — one fixed suite of 147 BVA/EP cases runs
  against every system by discovering endpoints from each app's own
  `create_apis.json`; no per-system test adaptation.
- **State-verified workflow checks** — after each lifecycle transition the
  harness re-reads the affected entity instead of trusting the HTTP response,
  so a route that returns 200 without changing state fails.
- **Auditable measurements** — every aggregate resolves back to a test case, a
  trace entry, a source function, a graph edge, a conflict weight, or a named
  interaction witness. All of it is committed under `reports/`.
- **Static analysis needs no running app** — stages 3 and 5 read source
  directly, so a system that fails the execution gate is still measured
  architecturally.

## Pipeline

```
┌──────────────────────┐    ┌──────────────────┐    ┌────────────────────────┐
│ Architecture-driven  │───▶│ 1. LLM-based     │───▶│ Agent-generated        │
│ prompt (QA-centric)  │    │    coding agent  │    │ artifacts:             │
│ • domain constraints │    └──────────────────┘    │ • source + start cmd   │
│ • 7-step workflow    │                            │ • create_apis.json     │
│ • 6 named tactics    │                            │ • nfr-trace.json       │
└──────────────────────┘                            │ • ADR + NFR matrix     │
                                                    └───────────┬────────────┘
                        ┌───────────────────────────────────────┼──────────────┐
                        ▼                                       ▼              ▼
          ┌──────────────────────────┐   ┌────────────────────────────┐  ┌───────────┐
          │ 2. Dynamic validation    │   │ 3. Static validation       │  │ 4. Quali- │
          │ executability →          │   │ tactic conformance +       │  │ tative:   │
          │ functional → workflow    │   │ conflict exposure (TICS)   │  │ ADR read  │
          │        (RQ1)             │   │        (RQ2, RQ3)          │  │           │
          └────────────┬─────────────┘   └─────────────┬──────────────┘  └─────┬─────┘
                       └───────────────────┬───────────┴───────────────────────┘
                                           ▼
                            Multi-dimensional evaluation results
```

Dynamic stages need the generated app running and reachable; static stages read
the frozen source tree. The two paths are independent by design — a system may
fail the execution gate and still be measured for architectural realization.

## Evaluation Metrics

### Tactic conformance (RQ2)

For each claimed tactic–function pair `(t, f)`:

```
V(f) = 1  if f exists and has a non-trivial body, else 0
       (a body of only pass / ... / a docstring / bare return /
        raise NotImplementedError counts as a stub)

L(t,f) = 1  if no external library is claimed, or the claimed library is
            reached from f — directly, through an instance attribute the
            class assigns, or through one received by constructor injection
         0  if a library is claimed but never reached

S(t,f) = V(f) * (0.5 + 0.5 * L(t,f))          ->  0, 0.5, or 1
```

Aggregation uses the **fixed** six-tactic catalog in every denominator, so a
requested tactic omitted from the trace scores zero rather than vanishing from
the measurement:

```
impl(t)  = mean over f in trace(t) of S(t,f)      ( = 0 if trace(t) is empty )
conf(q)  = mean over t in T_q of impl(t)          q in {performance, availability}
Conf     = mean over q of conf(q)
```

Averaging within each quality attribute first gives performance and availability
equal weight despite containing different numbers of tactics.

### Architectural interaction (RQ3)

Each backend is parsed into a function graph whose nodes use the same
`path::qualified_name` scheme as the trace. Edges are `CALLS` (statically
resolved first-party calls) and `REGISTERED` (framework-mediated relationships
with no ordinary call site — middleware, exception handlers, dependency
injection). Distance `d` is measured on the **undirected** graph, because two
tactics may meet at a common caller without either invoking the other.

```
delta(d) = 1 / (1 + d)   for finite d,  delta(inf) = 0      ( d_max = 6 hops )

C(ti,tj) = max over fi in trace(ti), fj in trace(tj) of
               sqrt( S(ti,fi) * S(tj,fj) ) * delta( d(fi,fj) )

TICS = sum over p in P+ of w(p)*C(p)  /  sum over p in P+ of w(p)
n+   = number of pairs in P+ with C(p) > 0
```

The geometric mean requires evidence from **both** tactics, so one strongly
bound tactic cannot compensate for a weakly bound one. The maximum is used
because the question is existential — do these two tactics meet anywhere — and
it preserves a concrete witness pair that can be inspected by hand. Ties break
by shorter distance, then lexicographically, so the reported witness is
reproducible.

TICS factors exactly into coverage × intensity, and should be read that way:

```
Cov = sum of w(p) over pairs with C(p) > 0  /  sum of w(p) over all of P+
Int = TICS / Cov          (0 when no interaction is found)
TICS = Cov * Int
```

> **TICS is not a quality score.** A high value may mean conflicting tactics
> were deliberately coordinated in one place; a low value may simply mean few
> tactics were realized, so few could collide. Always read it beside
> conformance and `n+`.

### Conflict model

Fixed before any system was inspected and applied identically to all four. Of
the 15 unordered pairs among six tactics, two are supporting (weight 0, excluded
from TICS) and thirteen form the conflict set `P+`, with `W+ = 6.6`.

| | 1.1 | 1.2 | 2.1 | 2.2 | 2.3 | 2.4 |
|---|---|---|---|---|---|---|
| **1.1** Limit Event Response | – | 0.25 | 0.25 | 0.25 | 0.50 | 0.75 |
| **1.2** Maintain Multiple Copies of Data | | – | 0.25 | **0.00** | 0.50 | 1.00 |
| **2.1** Exception Detection | | | – | 0.25* | 0.25 | 0.75 |
| **2.2** Graceful Degradation | | | | – | **0.00** | 1.00 |
| **2.3** State Resynchronization | | | | | – | 0.60 |
| **2.4** Transactions | | | | | | – |

`0.00` marks a supporting pair. `*` marks a relation that is disputed in the
literature. The weights operationalize interaction strength for this study; they
are author-defined from architectural literature, not canonical constants. The
machine-readable source of truth is
[`validators/tics/data/conf_tacticset.json`](method_pipeline_v2/validators/tics/data/conf_tacticset.json),
which carries a rationale string per pair.

## Results

Measured 2026-08-31 on Windows 11, Python 3.12.10, Docker 28.0.4.

| | `claude` | `codex` | `chatdev-v1` | `chatdev-v2` |
|---|---|---|---|---|
| Config lines changed to run | 0 | 1 | 1 | n/a |
| **Functional** (147 cases) | **98.0%** | 97.3% | 76.9% | **1.4%** |
| **Workflow** (19 checks) | **100%** | **100%** | 36.8% | 36.8% |
| **Conformance** | 0.818 | **0.984** | 0.781 | 0.587 |
| **TICS** | 0.166 | 0.443 | 0.071 | 0.240 |
| pairs found `n+` | 5/13 | 13/13 | 3/13 | 11/13 |
| coverage · intensity | 0.492 · 0.338 | 1.000 · 0.443 | 0.227 · 0.314 | 0.811 · 0.296 |
| median witness distance | 2 | 1 | 3 | 2 |

The orderings disagree, which is the point: `chatdev-v1` sits 0.037 below
`claude` on conformance while satisfying 7 of 19 workflow checks against
`claude`'s 19, and `chatdev-v2` still shows partial architectural realization
(0.587) while answering 1.4% of the functional suite.

Full analysis, failure attribution and measurement corrections:
[`reports/RESULTS.md`](method_pipeline_v2/reports/RESULTS.md).

## Installation

### Prerequisites

| Requirement | Version | Purpose |
|---|---|---|
| Python | 3.12+ | Pipeline, validators, metrics |
| Docker | Any recent | Stage 1 (compilability) and running the generated apps |
| uv | 0.12+ | Dependency management (or use `pip`) |
| LLM API access | — | Generation phase only; not needed to re-run validation |

Re-running the **validation** stages on the committed corpus needs no LLM key:
the four generated systems are in the repository.

```bash
git clone https://github.com/swinilab/llmagent4code.git
cd llmagent4code
uv sync                      # or: pip install -r requirements.txt
```

## Quick Start

Re-measure the architectural stages on the committed corpus — no app needs to be
running, no API key needed:

```bash
cd method_pipeline_v2

# Stage 3 — tactic conformance
python main.py --phase val --stage 3 --config pipeline_config.yaml

# Stage 5 — conflict exposure (TICS)
python main.py --phase val --stage 5 --config pipeline_config.yaml

# read what came out
cat reports/static_qa_claude_*/report.txt
cat reports/tics_claude_*/report.txt
```

All commands run **from `method_pipeline_v2/`** — modules import each other by
flat name (`from pipeline import run_pipeline`), so it must be the working
directory.

## Experiment Workflow

### Step 1 — Configure a Run

Copy the example and edit it; `pipeline_config.yaml` itself is not committed:

```bash
cp pipeline_config.yaml.example pipeline_config.yaml
```

| Key | Meaning |
|---|---|
| `agent.type` / `model` / `api_key` | Generation backend (`chatdev`, `mini`) and the model it drives |
| `agent.prompt_template` | Generation prompt. The corpus was produced from [`prompts/latest.md`](method_pipeline_v2/prompts/latest.md) |
| `validation.code` | Path of the system under test when running `--phase val` standalone |
| `validation.http.base_url` | Where the running app is reachable for stages 2 and 6 |
| `validator.nfr_trace_filename` | Trace file read by stages 3 and 5 (default `nfr-trace.json`) |
| `validator.expect_workflow_manifest` | Whether this prompt version required `workflow_apis.json`; `latest.md` does not — see [`docs/workflow_dependency_test_cases.md`](docs/workflow_dependency_test_cases.md) |
| `output.report_dir` | Report root (default `reports/`) |

Point `validation.code` at the application root — the directory that contains
`create_apis.json` and `nfr-trace.json`. For the ChatDev systems that is
`generated/<app>/code_workspace`, not `generated/<app>`.

### Step 2 — Generate an Application

```bash
python main.py --phase gen
```

The agent is called with the prompt named in the config and writes into
`agent.generated_dir`. Skip this step to evaluate the committed corpus.

### Step 3 — Run the Dynamic Stages

Stages 1, 2 and 6 need the system under test **running** and reachable at
`validation.http.base_url`:

```bash
cd generated/claude && docker compose up -d && cd -

python main.py --phase val --stage 1    # executability: build, start, health probe
python main.py --phase val --stage 2    # 147 BVA/EP functional cases
python main.py --phase val --stage 6    # 19 lifecycle workflow checks
```

Stage 2 discovers each entity's create endpoint from the app's own
`create_apis.json`; stage 6 discovers lifecycle transitions from the app's
OpenAPI description and supports both dedicated action routes
(`POST {orders}/{id}/accept`) and generic status setters
(`PUT {orders}/{id}/status`).

### Step 4 — Run the Static Stages

Stages 3 and 5 read source only:

```bash
python main.py --phase val --stage 3    # tactic conformance
python main.py --phase val --stage 5    # TICS
```

Stage 5 consumes stage 3's per-function confidences, so run 3 before 5 for a
system you have just added.

> `--phase val` with no `--stage` runs the 1→3 waterfall and stops at the first
> failure. Stages 5 and 6 must be requested explicitly. Stage 4 (dynamic NFR
> measurement under load and fault injection) is a placeholder and is not part
> of the reported results.

### Step 5 — Read the Reports

Each run writes `reports/<stage>_<app>_<timestamp>/` containing a
human-readable `report.txt` plus the JSON the numbers come from:

```
reports/
├── functional_test_claude_20260831_122237/functional_test_report.json
├── workflow_test_claude_20260831_122254/workflow_test_report.json
├── static_qa_claude_20260831_165805/static_qa_report.json    # score_func / score_tactic / score_qa
├── tics_claude_20260831_165809/
│   ├── tics_report.json        # per-pair weight, score, distance, witness functions, path
│   ├── tics_bindings.json      # every claimed tactic-function binding
│   └── tics_graph.json         # the recovered function graph (nodes + CALLS/REGISTERED edges)
└── RESULTS.md                  # the full write-up
```

`tics_report.json` keeps the witness pair and the hop path behind every non-zero
score, so any reported interaction can be opened in the generated source and
checked by hand.

## Repository Structure

```
llmagent4code/
├── method_pipeline_v2/
│   ├── main.py                     # entry point: --phase {gen,val,all} --stage {1..6}
│   ├── pipeline.py                 # generation + validation waterfall
│   ├── pipeline_factory.py         # dependency injection from the YAML config
│   ├── pipeline_config.yaml.example
│   ├── report_writer.py            # report.txt renderer
│   ├── agents/                     # generation backends (chatdev.yaml, mini.yaml, gen.py)
│   ├── interfaces/base.py          # GenerationResult / ValidationResult / Status contracts
│   ├── prompts/
│   │   └── latest.md               # THE architecture-driven prompt used for the corpus
│   ├── generated/                  # the four evaluated systems (frozen application source)
│   │   ├── claude/  codex/
│   │   └── chatdev-qwen35-v1/  chatdev-qwen35-v2/   (app root is code_workspace/)
│   ├── validators/
│   │   ├── CompilabilityValidator.py        # stage 1
│   │   ├── FunctionalValidator.py           # stage 2
│   │   ├── StaticQualityAttributeValidator.py  # stage 3 — S(t,f), impl(t), conf(q)
│   │   ├── WorkflowValidator.py             # stage 6
│   │   ├── tics/                            # stage 5
│   │   │   ├── TICSValidator.py             # orchestration + report emission
│   │   │   ├── scoring.py                   # C(ti,tj), TICS, coverage, intensity
│   │   │   ├── model.py                     # CodeGraph, FunctionNode, CALLS / REGISTERED
│   │   │   ├── extractors/python_extractor.py  # AST -> function graph
│   │   │   └── data/conf_tacticset.json     # the 15-pair conflict weight model
│   │   └── tests/
│   │       ├── test_groups/                 # 147 BVA/EP cases, one group per entity
│   │       ├── workflow_suite.py            # the 19 lifecycle checks
│   │       └── scoring/                     # unit tests for the scoring engine
│   └── reports/                    # committed measurement artifacts + RESULTS.md
├── docs/
│   ├── OMS_TestCases_BVA_EP_EN.xlsx         # the functional oracle, one sheet per entity
│   ├── workflow_dependency_test_cases.md    # which cases depend on lifecycle state
│   └── CHANGES.md
└── pyproject.toml
```

## Case Study: OrderMan

OrderMan is a customer-order-management system adapted from the UML
order-handling example, with five entities — Customer, Product, Order, Invoice,
Payment — connected by the relationships the domain requires. It is used here
because it carries both a non-trivial structural model and an explicit
cross-entity process, which lets local validation be separated from system-level
integration.

- **Field constraints** — [`prompts/latest.md`](method_pipeline_v2/prompts/latest.md)
  fixes type, required status, bounds, length, regex, allowed values, referential
  conditions and client-supplied vs server-derived status per attribute. These
  are the oracle for the 147 cases (customer 50, product 25, order 28, invoice
  26, payment 18).
- **Lifecycle** — `PLACED → ACCEPTED → INVOICED → PAID → VERIFIED → SHIPPED →
  CLOSED`, evaluated by 19 checks: 7 capability, 7 happy-path, 5 precondition
  (invalid out-of-order transitions must be rejected).
- **Tactics** — NFR 1.1 Limit Event Response and 1.2 Maintain Multiple Copies of
  Data (performance); NFR 2.1 Exception Detection, 2.2 Graceful Degradation,
  2.3 State Resynchronization, 2.4 Transactions (availability).

The prompt fixes the domain, the workflow, the six tactics and the evaluation
interfaces. It deliberately leaves language, web framework, persistence,
caching, transaction and rate-control mechanisms, and the placement of tactics
to the agent — and it explicitly permits one function to serve several tactics,
so observed co-location is an outcome, not a prompt violation.

## Corpus

| App | Agent | Stack | Path |
|---|---|---|---|
| `claude` | Claude Code | FastAPI + Postgres (primary + streaming replica) + Redis | [`generated/claude`](method_pipeline_v2/generated/claude) |
| `codex` | Codex | FastAPI + Postgres + Redis + Prometheus | [`generated/codex`](method_pipeline_v2/generated/codex) |
| `chatdev-v1` | ChatDev / Qwen3.5-cloud | FastAPI + Postgres + Redis | [`generated/chatdev-qwen35-v1`](method_pipeline_v2/generated/chatdev-qwen35-v1) |
| `chatdev-v2` | ChatDev / Qwen3.5-cloud | FastAPI + SQLite | [`generated/chatdev-qwen35-v2`](method_pipeline_v2/generated/chatdev-qwen35-v2) |

All four were generated from the same prompt with no agent-specific follow-up,
correction or architectural hint. Application source is frozen: only non-source
configuration changes needed to launch an artifact were permitted, and each is
recorded in [`reports/executability/`](method_pipeline_v2/reports/executability).
The two ChatDev runs share an agent, a model and a command and differ only in
the sampled trajectory, which is why they are reported separately.

## Reproducing the Paper's Tables

Every cell traces to a committed artifact:

| Paper value | Artifact |
|---|---|
| Functional pass rates | `reports/functional_test_<app>_*/functional_test_report.json` → `summary[].passed` |
| Workflow 7 / 7 / 5 breakdown | `reports/workflow_test_<app>_*/workflow_test_report.json` → `summary[]` |
| Conformance, `impl(t)`, `S(t,f)` | `reports/static_qa_<app>_*/static_qa_report.json` → `scoring_summary` |
| TICS, `n+`, per-pair `C`, witnesses | `reports/tics_<app>_*/tics_report.json` → `score`, `pairs[]` |
| Coverage / intensity / median `d` | derived from `pairs[]`: weights of scoring pairs vs. of pairs with `score > 0` |
| Conflict weights `w(p)`, `W+` | `validators/tics/data/conf_tacticset.json` |

`chatdev-v1` appears twice in the functional reports on purpose: as generated it
passes 81/147 (55.1%), which measures a database schema that was never mounted;
after the one-line mount it passes 113/147 (76.9%), which measures its
validation logic. The paper reports the second, because `codex` received an
equivalent one-line configuration fix before being measured.

## Development

```bash
python -m pytest method_pipeline_v2/validators -q
```

The suite covers the scoring engine and includes an oracle test that pins the
`codex` TICS run end to end — an accidental edit to a conflict weight silently
rescales every reported TICS number, so that test guards the weight table.

**Adding a system to the corpus**

1. Put the frozen application source under `generated/<name>/`, including
   `create_apis.json`, `nfr-trace.json` and `start_command.txt`.
2. Point `validation.code` at the directory that holds those files.
3. Run stage 3, then stage 5 (stage 5 consumes stage 3's confidences).
4. For dynamic stages, start the app first and set `validation.http.base_url`.

**Extending the static analysis**

- The function graph is built by `validators/tics/extractors/python_extractor.py`;
  a new language means a new extractor emitting the same `CodeGraph` of
  `path::qualified_name` nodes with `CALLS` / `REGISTERED` edges.
- Conflict weights live in `validators/tics/data/conf_tacticset.json`. Changing
  one changes every TICS number in the corpus — update the oracle test in the
  same commit.
- Conformance deliberately does **not** depend on the graph. Keep it that way:
  an earlier formulation required a claimed function to be graph-connected,
  which made the measure sensitive to extractor incompleteness rather than to
  implementation evidence.

## Citation

If you find this repository useful, please consider giving a ⭐ or citing:

```bibtex
@inproceedings{nguyen2026archdriven,
  title     = {Towards Architecture-Driven Code Generation with LLM-based
               Coding Agent: An Empirical Study},
  author    = {Nguyen, Cong Van and Le, Duc Minh and Nguyen, Manh Duc and
               Hoang, Khue Minh},
  year      = {2026}
}

@misc{nguyen2026modeltwintr,
  title  = {Towards Model-Twin Software Development: LLM-Augmented
            Annotation-Based Domain-Driven Code Generation},
  author = {Nguyen, Cong Van and Le, Duc Minh},
  year   = {2026},
  note   = {Technical Report},
  url    = {https://drive.google.com/file/d/14LbqCPxYrkw3Q2xwxmNWQURzb3qXWjV2}
}
```

### Related work

- **Architectural tactics** — Bass, L., Clements, P., Kazman, R. *Software
  Architecture in Practice*, 4th ed. Addison-Wesley (2021)
- **Prior architecture-driven study** — Le, D.M., Pham, C.Y.L., Truong, S.D.,
  Vu, A.H.P. *Towards Architecture-Driven Code Generation with Generative AI:
  An Empirical Study.* ICIIT (2026)
- **AGL** — Dang, D.H., Le, D.M., Le, V.V. *AGL: Incorporating behavioral
  aspects into domain-driven design.* Information and Software Technology 163,
  107284 (2023)
- **JDA** — Le, D.M., Dang, D.H., Vu, H.T. *jDomainApp: A module-based
  domain-driven software framework.* SoICT '19, 399–406 (2019)
- **Model Twin** — [jdomainapp/jdai-genmt](https://github.com/jdomainapp/jdai-genmt)

## Acknowledgements

The authors thank Chi Le Yen Pham, Duc Anh Le and other members of the Software
Innovation Lab, Swinburne Vietnam (SWELab) for constructive discussions,
technical feedback, and assistance with the experimental setup, evaluation
process and replication artifacts.

## Contact

For questions about this work, please contact:
`congnv24@fe.edu.vn` and `duclm20@fe.edu.vn`.
