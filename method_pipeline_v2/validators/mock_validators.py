"""
validators/mock_validators.py
──────────────────────────────
Mock implementations of ICompilabilityValidator and IFunctionalValidator.

They inspect the code string for sentinel tokens planted by the mock
scenarios so the pipeline logic can be exercised without Docker or a
running server.

Real implementations would:
  - CompilabilityValidator:  
    + Start Docker using the command in /start_command.txt
    + Wait for Docker start command to completed running
    + Capture any exit code/stderr
    + Return ValidationResult
  - FunctionalValidator     
    + httpx / requests against a live container
"""

from __future__ import annotations

from interfaces.base import (
    ICompilabilityValidator,
    IFunctionalValidator,
    Status,
    ValidationResult,
)
from pathlib import Path


_COMPILE_FAIL_TOKEN    = "# MOCK:COMPILE_FAIL"
_FUNCTIONAL_FAIL_TOKEN = "# MOCK:FUNCTIONAL_FAIL"


class MockCompilabilityValidator(ICompilabilityValidator):
    def validate(self, code: str) -> ValidationResult:
        def __init__(self, config: dict) -> None:
            self._generated_dir = Path(
                config.get("agent", {}).get("generated_dir", "generated")
            )
        if _COMPILE_FAIL_TOKEN in code:
            return ValidationResult(
                stage="compilability",
                status=Status.FAIL,
                message="SyntaxError: invalid syntax at line 7 (mock)",
                details={
                    "docker_image": "python:3.11-slim",
                    "exit_code": 1,
                    "stderr": "SyntaxError: invalid syntax",
                },
            )
        return ValidationResult(
            stage="compilability",
            status=Status.PASS,
            message="Code compiled successfully inside Docker.",
            details={"docker_image": "python:3.11-slim", "exit_code": 0},
        )


class MockFunctionalValidator(IFunctionalValidator):
    def __init__(self, endpoints: list[dict] | None = None) -> None:
        self._endpoints = endpoints or [
            {"id": "health_check", "method": "GET",  "path": "/health",    "expected_status": 200},
            {"id": "create_item",  "method": "POST", "path": "/items",     "expected_status": 201},
            {"id": "get_item",     "method": "GET",  "path": "/items/1",   "expected_status": 200},
            {"id": "invalid_item", "method": "GET",  "path": "/items/9999","expected_status": 404},
        ]

    def validate(self, code: str) -> ValidationResult:
        results = []
        for ep in self._endpoints:
            if _FUNCTIONAL_FAIL_TOKEN in code and ep["id"] == "create_item":
                results.append({
                    "id": ep["id"],
                    "status": "FAIL",
                    "expected": ep["expected_status"],
                    "actual": 500,
                    "error": "Internal Server Error (mock)",
                })
            else:
                results.append({
                    "id": ep["id"],
                    "status": "PASS",
                    "expected": ep["expected_status"],
                    "actual": ep["expected_status"],
                })

        failed = [r for r in results if r["status"] == "FAIL"]

        if failed:
            return ValidationResult(
                stage="functional",
                status=Status.FAIL,
                message=f"{len(failed)} of {len(results)} HTTP test(s) failed.",
                details={"results": results, "failed": failed},
            )
        return ValidationResult(
            stage="functional",
            status=Status.PASS,
            message=f"All {len(results)} HTTP functional tests passed.",
            details={"results": results},
        )