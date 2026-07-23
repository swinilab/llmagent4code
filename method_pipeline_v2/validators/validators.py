"""
validators/real_validators.py
──────────────────────────────
Real implementations of ICompilabilityValidator and IFunctionalValidator.
"""
from __future__ import annotations

import subprocess
import httpx
import os
from pathlib import Path
import json

from interfaces.base import (
    ICompilabilityValidator,
    IFunctionalValidator,
    Status,
    TestResult,
    ValidationResult,
    GenerationResult
)
from validators.tests.CustomerTestGroup import CustomerTestGroup


class CompilabilityValidator(ICompilabilityValidator):
    """
    Real Compilability Validator:
    - Reads the startup command from /start_command.txt
    - Executes it via subprocess (e.g. starting a Docker container)
    - Captures exit codes, stdout, and stderr
    """
    def __init__(self, config: dict | None = None) -> None:
        config = config or {}
        self._generated_dir = Path(
            config.get("agent", {}).get("generated_dir", "generated")
        )
        # Default to /start_command.txt as requested, but allow override via config
        self._start_command_file = config.get("validator", {}).get("start_command_file", "start_command.txt")

    def validate(self, generation_result: GenerationResult, code: str) -> ValidationResult:
        workdir = os.path.join(
                self._generated_dir,
                generation_result.output_dir,
                "code_workspace")
        # 1. Read the Docker start command
        try:
            command = Path(os.path.join(
                workdir,
                self._start_command_file
            )).read_text().strip()
        except FileNotFoundError:
            return ValidationResult(
                stage="compilability",
                status=Status.FAIL,
                message=f"Start command file not found: {self._start_command_file}",
                details={"error": "FileNotFoundError"},
            )
        except Exception as e:
            return ValidationResult(
                stage="compilability",
                status=Status.FAIL,
                message=f"Failed to read command file: {e}",
                details={"error": str(e)},
            )

        # 2. Execute the command and wait for completion
        try:
            proc = subprocess.run(
                command,
                shell=True,            # Allows pipes, redirects, etc.
                capture_output=True,   # Captures stdout/stderr
                text=True,             # Decodes output to string
                cwd=workdir,
            )

            # 3. Check exit code and return appropriate ValidationResult
            if proc.returncode != 0:
                return ValidationResult(
                    stage="compilability",
                    status=Status.FAIL,
                    message=f"Docker start command failed with exit code {proc.returncode}.",
                    details={
                        "command": command,
                        "exit_code": proc.returncode,
                        "stderr": proc.stderr,
                        "stdout": proc.stdout,
                    },
                )

            return ValidationResult(
                stage="compilability",
                status=Status.PASS,
                message="Docker start command completed successfully.",
                details={
                    "command": command,
                    "exit_code": proc.returncode,
                    "stdout": proc.stdout,
                },
            )
        except Exception as e:
            return ValidationResult(
                stage="compilability",
                status=Status.FAIL,
                message=f"Exception while running start command: {e}",
                details={"error": str(e), "command": command},
            )


class FunctionalValidator(IFunctionalValidator):
    """
    Real Functional Validator:
    - Fires live HTTP requests using httpx against the running container
    - Validates actual HTTP status codes against expected status codes
    """
    def __init__(
        self, 
        endpoints: list[dict] | None = None, 
        config: dict | None = None
    ) -> None:
        config = config or {}
        self._base_url = config.get("validator", {}).get("base_url", "http://localhost:8000")
        self._timeout = config.get("validator", {}).get("timeout", 10.0)
        self._generated_dir = Path(
            config.get("agent", {}).get("generated_dir", "generated")
        )
        # Default to /start_command.txt as requested, but allow override via config
        self._start_command_file = config.get("validator", {}).get("start_command_file", "start_command.txt")

    def validate(self, generation_result: GenerationResult, code: str) -> ValidationResult:
        workdir = os.path.join(
                self._generated_dir,
                generation_result.output_dir,
                "code_workspace")
        create_api_paths = dict()
        with open(os.path.join(workdir, 'create_apis.json'), 'r', encoding='utf-8') as file:
            create_api_paths = json.load(file)
        
        results = list[TestResult]()

# TODO: add similar blocks for the remaining entities
        customer_create_api = "/api/v1/customers"
        if create_api_paths["customer"] is not None and create_api_paths["customer"]["path"] is not None:
            customer_create_api = create_api_paths["customer"]["path"]
        customer_group = CustomerTestGroup(api = self._base_url + customer_create_api)
        results.extend(customer_group.run_all())
                    
        failed = [r for r in results if r.result == False]
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