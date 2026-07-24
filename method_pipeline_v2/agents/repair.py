import os
import shutil
import subprocess
from pathlib import Path

from interfaces.base import IRepairAgent, ValidationResult

class MiniRepairAgent(IRepairAgent):
    def __init__(self, config: dict) -> None:
        self._config = config.get("repair", {})
        self._llm = self._config.get("model", "gpt-4o")
        
        # Use .resolve() to convert to an absolute path (e.g., /home/swe/.../agents/mini.yaml)
        workdir = config.get("workdir", ".")
        workflow_file = self._config.get("workflow", "mini.yaml")
        
        self._agent_config_path = (Path(workdir) / workflow_file).resolve()

    def repair(
        self,
        code: str,
        validation_result: ValidationResult,
        iteration: int,
    ) -> str:
        # Resolve paths to transition from sdk-{k-1} to sdk-{k}
        current_workspace = Path(code)
        source_sdk_dir = current_workspace.parent
        generated_dir = source_sdk_dir.parent
        
        target_sdk_dir = generated_dir / f"sdk-{iteration}"
        
        # Clean up target directory if it already exists from a previous aborted run
        if target_sdk_dir.exists():
            shutil.rmtree(target_sdk_dir)
            
        # Copy the entire sdk environment for the next iteration
        shutil.copytree(source_sdk_dir, target_sdk_dir)
        
        # Define the new working directory for the mini agent
        new_workspace = target_sdk_dir / current_workspace.name
        
        # Extract error logs to feed into the agent
        error_detail = validation_result.details.get("stderr") or validation_result.details.get("error") or "Unknown error"
        
        task_prompt = (
            f"The application failed validation.\n"
            f"Error details:\n{error_detail}\n\n"
            f"Review the files and fix the bug."
        )
        
        # Construct the execution command leveraging uv and mini
        command = [
            "uv",
            "run",
            "mini",
            "--config", str(self._agent_config_path),
            "--task", task_prompt,
            "--model", "ollama/" + self._llm,
            "--yolo",
            "--exit-immediately",
            "--environment-class", "local"
        ]
        
        try:
            current_env = os.environ.copy()
            
            subprocess.run(
                command,
                check=True,
                text=True,
                env=current_env,
                cwd=str(new_workspace),
            )
            print(f"Repair iteration {iteration} completed.")
            
        except subprocess.CalledProcessError as e:
            print(f"Repair iteration {iteration} encountered an error. Exit code: {e.returncode}")
            print(e.stderr)
        except FileNotFoundError:
            print("Execution failed. Verify that 'uv' is installed and accessible in the system path.")
            
        # Return the path to the newly repaired workspace
        return str(new_workspace)