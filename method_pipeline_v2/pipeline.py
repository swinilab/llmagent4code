"""
This file owns the workflow logic:
  1. Generation     → call agent with prompt
  2. Validation     → compilability (Docker) ► functional tests (HTTP)  [waterfall]
  3. Repair loop    → up to k iterations, re-validating after each repair
  4. Report         → report.txt (error detail or "check QA manually")

All behaviour is injected via pipeline_factory.build().
"""

from __future__ import annotations
import sys
from interfaces.base import GenerationResult, RepairResult, ValidationResult
from pipeline_factory import PipelineComponents


def _read_prompt(config: dict) -> str:
    path = config.get("agent", {}).get("prompt_template", "")
    try:
        with open(path) as f:
            return f.read().strip()
    except FileNotFoundError:
        return (
            "Generate a minimal FastAPI service with /health, "
            "POST /items, and GET /items/{id} endpoints."
        )

def run_generation(components: PipelineComponents, prompt: str) -> GenerationResult:
    print("PHASE 1: GENERATE ORDERMAN")
    result = components.generation_agent.generate(prompt)
    print("  ✅ done")
    return result

def run_validation(components: PipelineComponents, code: str, indent: int = 1) -> list[ValidationResult]:
    pad = "  " * indent
    results: list[ValidationResult] = []

    print(f"{pad}validate > compilability")
    compile_result = components.compilability_validator.validate(code)
    results.append(compile_result)

    if not compile_result.passed:
        print(f"{pad}  ❌ {compile_result.message}")
        return results
    print(f"{pad}  ✅ passed")

    print(f"{pad}validate > functional tests")
    functional_result = components.functional_validator.validate(code)
    results.append(functional_result)

    if not functional_result.passed:
        print(f"{pad}  ❌ {functional_result.message}")
    else:
        print(f"{pad}  ✅ passed")

    return results

def run_repair_loop(
    components: PipelineComponents,
    code: str,
    first_failure: ValidationResult,
    max_iterations: int,
) -> tuple[str, list[RepairResult]]:
    repair_history: list[RepairResult] = []
    current_code    = code
    current_failure = first_failure

    for iteration in range(1, max_iterations + 1):
        print(f"  repair > iteration {iteration}/{max_iterations}")

        current_code = components.repair_agent.repair(
            code=current_code,
            validation_result=current_failure,
            iteration=iteration,
        )

        iter_results = run_validation(components, current_code, indent=2)
        all_passed   = all(vr.passed for vr in iter_results)

        repair_history.append(RepairResult(
            iteration=iteration,
            repaired_code=current_code,
            validation_results=iter_results,
            all_passed=all_passed,
        ))

        if all_passed:
            break

        for vr in iter_results:
            if not vr.passed:
                current_failure = vr
                break

    return current_code, repair_history

def run_pipeline(components: PipelineComponents, phase: str = "all") -> None:
    cfg            = components.config
    max_iterations = cfg.get("repair", {}).get("max_iterations", 3)
    prompt         = _read_prompt(cfg)

    generation         = None
    validation_results = []
    repair_history     = []
    first_failure      = None
    code               = ""

    if phase in ("gen", "all"):
        generation = run_generation(components, prompt)

    if phase in ("val", "all"):
        print("PHASE 2: VALIDATION")
        validation_results = run_validation(components, code, indent=1)
        first_failure      = next((vr for vr in validation_results if not vr.passed), None)

    if phase in ("re", "all") and first_failure is not None:
        print("PHASE 3: REPARATION")
        code, repair_history = run_repair_loop(
            components=components,
            code=code,
            first_failure=first_failure,
            max_iterations=max_iterations,
        )
        if repair_history:
            validation_results = repair_history[-1].validation_results

    print("EXPORTING REPORT")
    all_passed  = all(vr.passed for vr in validation_results)
    report_path = components.report_writer.write(
        generation=generation,
        validation_results=validation_results,
        repair_history=repair_history,
        all_passed=all_passed,
    )

    if all_passed:
        print(f"  ✅ done → {report_path} (check QA manually)")
    else:
        print(f"  ❌ failed → {report_path}")
        sys.exit(1)