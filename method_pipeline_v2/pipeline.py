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
from pathlib import Path
from interfaces.base import GenerationResult, RepairResult, ValidationResult
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
    return result

def run_validation(components: PipelineComponents, gen_result: str, code: str, indent: int = 1) -> list[ValidationResult]:
    pad = "  " * indent
    results: list[ValidationResult] = []

    print(f"{pad}validate > compilability")
    compile_result = components.compilability_validator.validate(gen_result, code)
    results.append(compile_result)

    if not compile_result.passed:
        print(f"{pad}  ❌ {compile_result.message}")
        return results
    print(f"{pad}  ✅ passed")

    # print(f"{pad}validate > functional tests")
    # functional_result = components.functional_validator.validate(gen_result, code)
    # results.append(functional_result)

    # if not functional_result.passed:
    #     print(f"{pad}  ❌ {functional_result.message}")
    # else:
    #     print(f"{pad}  ✅ passed")

    return results

def run_repair_loop(
    components: PipelineComponents,
    generation_result: GenerationResult,
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

        iter_results = run_validation(components,generation_result, current_code, indent=2)
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

    # Khởi tạo mặc định nếu bỏ qua pha Generation
    generation         = GenerationResult("lol", "sdk-0", True)
    validation_results = []
    repair_history     = []
    
    generated_dir = Path(cfg.get("agent", {}).get("generated_dir", "generated"))
    code          = str(generated_dir / generation.output_dir / "code_workspace")

    # 1. GENERATION PHASE
    if phase in ("gen", "all"):
        generation = run_generation(components, prompt)
        code = str(generated_dir / generation.output_dir)

    # 2. VALIDATION & REPAIR PHASE
    if phase in ("val", "all"):
        print("PHASE 2: VALIDATION & REPAIR")
        
        # Chạy kiểm tra ban đầu
        initial_validation_results = run_validation(components, generation, code, indent=1)
        first_failure = next((vr for vr in initial_validation_results if not vr.passed), None)

        # Nếu phát hiện lỗi, kích hoạt Repair Loop
        if first_failure is not None:
            print("  ❌ Errors detected. Initiating repair loop...")
            code, repair_history = run_repair_loop(
                components=components,
                generation_result=generation,
                code=code,
                first_failure=first_failure,
                max_iterations=max_iterations,
            )
            
            # Kết quả cuối cùng để quyết định all_passed
            final_validation_results = repair_history[-1].validation_results if repair_history else initial_validation_results
        else:
            print("  ✅ Validation passed on first try. No repair needed.")
            final_validation_results = initial_validation_results

    # 3. EXPORT REPORT
    print("EXPORTING REPORT")
    all_passed = all(vr.passed for vr in final_validation_results) if final_validation_results else False

    report_path = components.report_writer.write(
        generation=generation,
        validation_results=initial_validation_results, # Giữ nguyên log FAIL ban đầu ở đây
        repair_history=repair_history,
        all_passed=all_passed,
)

    if all_passed:
        print(f"  ✅ done → {report_path} (check QA manually)")
    else:
        print(f"  ❌ failed → {report_path}")
        sys.exit(1)

# def run_pipeline(components: PipelineComponents, phase: str = "all") -> None:
#     cfg            = components.config
#     max_iterations = cfg.get("repair", {}).get("max_iterations", 3)
#     prompt         = _read_prompt(cfg)

#     # generation         = GenerationResult("lol", "sdk_chatdev_20260711014413_20260711014413/", True)
#     generation         = GenerationResult("lol", "sdk-0/", True)

#     validation_results = []
#     repair_history     = []
#     first_failure      = None
#     code               = ""

#     if phase in ("gen", "all"):
#         generation = run_generation(components, prompt)
#         # pass

#     # generation.output_dir = "sdk_chatdev_20260711014413_20260711014413"

#     if phase in ("val", "all"):
#         print("PHASE 2: VALIDATION")
#         validation_results = run_validation(components, generation, code, indent=1)
#         first_failure      = next((vr for vr in validation_results if not vr.passed), None)

#     if phase in ("re", "all") and first_failure is not None:
#         print("PHASE 3: REPARATION")
#         code, repair_history = run_repair_loop(
#             components=components,
#             generation_result=generation,
#             code=code,
#             first_failure=first_failure,
#             max_iterations=max_iterations,
#         )
#         if repair_history:
#             validation_results = repair_history[-1].validation_results

#     print("EXPORTING REPORT")
#     all_passed  = all(vr.passed for vr in validation_results)
#     report_path = components.report_writer.write(
#         generation=generation,
#         validation_results=validation_results,
#         repair_history=repair_history,
#         all_passed=all_passed,
#     )

#     if all_passed:
#         print(f"  ✅ done → {report_path} (check QA manually)")
#     else:
#         print(f"  ❌ failed → {report_path}")
#         sys.exit(1)