from interfaces.base import GenerationResult, IGenerationAgent
import chatdev.sdk
import os
from pathlib import Path
from chatdev import run_workflow
import shutil


class ChatDevGenerationAgent(IGenerationAgent):
    def __init__(self, config) -> None:
        self._config = config.get("agent", {})

    def generate(self, prompt: str) -> GenerationResult:
        generated_dir = Path(self._config.get("generated_dir", "generated"))
        chatdev.sdk.OUTPUT_ROOT = generated_dir
        workdir = Path(self._config.get("workdir", "."))

        result = run_workflow(
            yaml_file=workdir / self._config.get("workflow"),
            task_prompt=prompt,
            variables={
                "BASE_URL":   self._config.get("api_base"),
                "API_KEY":    self._config.get("api_key"),
                "MODEL_NAME": self._config.get("model"),
            },
        )

        # Find the latest ChatDev's generated workspace
        final_output_dir = str(generated_dir)
        if result:
            # 1. Plan A: try to take directly from ChatDev's return
            if hasattr(result, "output_dir"):
                potential_dir = Path(result.output_dir) / "code_workspace"
            else:
                potential_dir = generated_dir / str(result) / "code_workspace"

            if potential_dir.exists() and potential_dir.is_dir():
                latest_dir = potential_dir.parent
            else:
                # 2. Plan B: Find the latest 'sdk-*' folder that contains 'workspace'
                subdirs = [d for d in generated_dir.iterdir() if d.is_dir() and d.name.startswith("sdk")]
                if subdirs:
                    # Sort chronologically
                    latest_dir = max(subdirs, key=lambda os_path: os_path.stat().st_mtime)
                else:
                    latest_dir = None

            if latest_dir:
                target_dir = generated_dir / "sdk-0"
                if target_dir.exists():
                    shutil.rmtree(target_dir)
                latest_dir.rename(target_dir)
                workspace_dir = target_dir / "code_workspace"
                if workspace_dir.exists():
                    final_output_dir = str(workspace_dir)

        return GenerationResult(
            model=self._config.get("model"),
            output_dir=final_output_dir,
            completion=True if result else False
        )