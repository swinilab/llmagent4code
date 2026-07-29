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
    return results

def run_pipeline(components: PipelineComponents, phase: str = "all") -> None:
    cfg    = components.config
    prompt = _read_prompt(cfg)

    generation: GenerationResult | None = None
    validation_results: list[ValidationResult] = []

    generated_dir = Path(cfg.get("agent", {}).get("generated_dir", "generated"))
    code          = str(generated_dir / "code_workspace")

    # 1. GENERATION PHASE
    if phase in ("gen", "all"):
        generation = run_generation(components, prompt)
        code = generation.code

    # 2. VALIDATION PHASE
    if phase in ("val", "all"):
        print("PHASE 2: VALIDATION")
        validation_results = run_validation(components, code, indent=1)

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
