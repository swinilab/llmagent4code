"""
This file owns the workflow logic:
  1. Generation     → call agent with prompt
  2. Validation     → compilability (Docker) ► functional tests (HTTP)  [waterfall]
  3. Report         → report.txt (error detail or "check QA manually")

All behaviour is injected via pipeline_factory.build().
"""

from __future__ import annotations
import sys
from pathlib import Path
from interfaces.base import GenerationResult, Status, ValidationResult
from pipeline_factory import PipelineComponents
import json


def _read_prompt(config: dict) -> str:
    workdir = Path(config.get("workdir", "."))

    rel_path = config.get("agent", {}).get("prompt_template", "")
    full_path = (workdir / rel_path).resolve()

    try:
        with open(full_path) as f:
            return f.read().strip()
    except FileNotFoundError:
        print(f"❌ Error: Prompt file not found at path: '{full_path}'")
        sys.exit(1)

def run_generation(components: PipelineComponents, prompt: str) -> GenerationResult:
    print("PHASE 1: GENERATE ORDERMAN")
    result = components.generation_agent.generate(prompt)
    print("  ✅ done")
    print(f"  status : {result.status}")
    print(f"  model  : {result.model}")
    print(f"  code   : {result.code}")
    return result

def _generation_result_from_config(cfg: dict) -> GenerationResult:
    """Build a stand-in GenerationResult for standalone `--phase val` runs,
    reading the code path to validate from the pipeline config."""
    code = cfg.get("validation", {}).get("code", "")
    return GenerationResult(status=Status.PASS, model="None", code=code)

# stage number -> human-readable name (1-3 are implemented, 4 is a placeholder)
VALIDATION_STAGES = {
    1: "compilability",
    2: "functional",
    3: "static QA",
    4: "QA",
}

def run_validation(
    components: PipelineComponents,
    generation: GenerationResult,
    stage: int | None = None,
    indent: int = 1,
) -> list[ValidationResult]:
    """Run the validation waterfall, or a single isolated sub-stage.

    stage=None runs stages 1→3 in a waterfall (stops at the first failure).
    stage=1|2|3|4 runs only that sub-stage, regardless of pass/fail.
    """
    pad = "  " * indent
    results: list[ValidationResult] = []
    stages = [stage] if stage is not None else [1, 2, 3]
    waterfall = stage is None

    for s in stages:
        name = VALIDATION_STAGES[s]

        if s == 1:
            print(f"{pad}validate > {name}")
            result = components.compilability_validator.validate(generation)
        elif s == 2:
            print(f"{pad}validate > {name}")
            result = components.functional_validator.validate(generation)
        elif s == 3:
            print(f"{pad}validate > {name}")
            result = components.static_quality_validator.validate(generation)
        else:
            print(f"{pad}validate > {name} (not implemented yet, skipping)")
            continue

        results.append(result)
        if result.passed:
            print(f"{pad}  ✅ passed")
        else:
            if s == 2:
                print(f"{pad}  ❌ {json.dumps(result.details)}")
            else:
                print(f"{pad}  ❌ {result.message}")
            # if waterfall:
            #     break

    return results

def run_pipeline(components: PipelineComponents, phase: str = "all", stage: int | None = None) -> None:
    cfg    = components.config
    prompt = _read_prompt(cfg)

    generation: GenerationResult | None = None
    validation_results: list[ValidationResult] = []

    # 1. GENERATION PHASE
    # if phase in ("gen", "all"):
    #     generation = run_generation(components, prompt)

    generation = GenerationResult('','','')
    generation.code = 'generated/sdk_chatdev_20260806222639_20260806222639/code_workspace'

    # 2. VALIDATION PHASE
    if phase in ("val", "all"):
        print("PHASE 2: VALIDATION")
        if generation is None:
            # standalone `--phase val` run: build the GenerationResult from config
            generation = _generation_result_from_config(cfg)
        validation_results = run_validation(components, generation, stage=stage, indent=1)

    # 3. EXPORT REPORT
    print("EXPORTING REPORT")
    if validation_results:
        all_passed = all(vr.passed for vr in validation_results)
    else:
        all_passed = generation is not None and generation.status is Status.PASS

    report_path = components.report_writer.write(
        generation=generation,
        validation_results=validation_results,
        all_passed=all_passed,
    )

    if all_passed:
        print(f"  ✅ done → {report_path} (please check QA manually)")
    else:
        print(f"  ❌ failed → {report_path}")
        sys.exit(1)
