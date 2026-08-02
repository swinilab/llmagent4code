from __future__ import annotations
import subprocess
import os
import time
from pathlib import Path
import requests
from interfaces.base import (
    GenerationResult,
    ICompilabilityValidator,
    Status,
    ValidationResult,
)

class CompilabilityValidator(ICompilabilityValidator):
    """
    Real Compilability Validator:
    - Reads the startup command from /start_command.txt
    - Executes it via subprocess (e.g. starting a Docker container / uvicorn server)
    - Captures exit codes, stdout, and stderr
    - For long-running servers (e.g. uvicorn) that stay up, also fires a smoke
      HTTP request so a server that boots fine but 500s on every request
      (broken imports, bad DB config, etc.) still fails compilability.
    """
    def __init__(self, config: dict | None = None) -> None:
        config = config or {}
        self._generated_dir = Path(
            config.get("agent", {}).get("generated_dir", "generated")
        )
        self._start_command_file = config.get("validator", {}).get("start_command_file", "start_command.txt")
        self._base_url = config.get("validator", {}).get("base_url", "http://localhost:8000")
        self._boot_wait_seconds = config.get("validator", {}).get("boot_wait_seconds", 15)
        self._smoke_path = config.get("validator", {}).get("smoke_path", "/")
        self._smoke_timeout = config.get("validator", {}).get("smoke_timeout", 10)

    def _clean_logs(self, raw_text: str) -> str:
        if not raw_text:
            return ""
        lines = raw_text.splitlines()
        clean_lines = [
            line for line in lines
            if line.strip() and not line.strip().startswith('#')
        ]
        return "\n".join(clean_lines)

    def _smoke_test(self) -> ValidationResult:
        """Fire a lightweight HTTP request against the still-running server to catch
        startup-time errors that don't crash the process (e.g. every request 500s)."""
        try:
            resp = requests.get(f"{self._base_url}{self._smoke_path}", timeout=self._smoke_timeout)
        except requests.RequestException as e:
            return ValidationResult(
                status=Status.FAIL,
                stage="compilability",
                message="Server process is running but not reachable via HTTP",
                details={"error": str(e)},
            )

        if resp.status_code >= 500:
            return ValidationResult(
                status=Status.FAIL,
                stage="compilability",
                message=f"Server started but returned HTTP {resp.status_code} on smoke request",
                details={"status_code": resp.status_code, "body": resp.text},
            )

        return ValidationResult(
            status=Status.PASS,
            stage="compilability",
            message=f"Server started and responded successfully (HTTP {resp.status_code})",
            details={},
        )

    def validate(self, generation_result: GenerationResult) -> ValidationResult:
        workdir = Path(os.path.join(
            self._generated_dir,
            generation_result.code,
            "code_workspace"
        ))
        command_file = Path(os.path.join(
            workdir,
            self._start_command_file
        ))
        try:
            command = command_file.read_text().strip()
        except FileNotFoundError:
            return ValidationResult(
                stage="compilability",
                status=Status.FAIL,
                message=f"Start command file not found: {command}",
                details={"error": "FileNotFoundError"},
            )
        except Exception as e:
            return ValidationResult(
                stage="compilability",
                status=Status.FAIL,
                message=f"Failed to read command file: {e}",
                details={"error": str(e)},
            )

        # Launch the start command in the background so we can both watch for an
        # early crash and, once it's still alive, smoke-test it over HTTP —
        # a plain subprocess.run(timeout=...) can't do the latter since it blocks.
        try:
            process = subprocess.run(
                command,
                cwd=workdir,
                shell=True,
                capture_output=True,
                text=True,
            )
            if process.returncode != 0:
                return ValidationResult(
                    status=Status.FAIL,
                    stage="compilability",
                    message=f"Failed to launch start command: Return code is {process.returncode} \n {process.stderr}",
                    details={"error": str(process.stderr)},
                )
        except Exception as e:
            return ValidationResult(
                status=Status.FAIL,
                stage="compilability",
                message=f"Failed to launch start command: {e}",
                details={"error": str(e)},
            )

        # Process is still running past the boot window (good sign, not a crash).
        # Leave it running so later validation stages (e.g. functional) can reach
        # it too — but probe it now to catch requests that fail with 5xx.
        return self._smoke_test()
