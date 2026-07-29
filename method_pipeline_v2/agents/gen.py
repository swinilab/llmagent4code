from interfaces.base import GenerationResult, IGenerationAgent, Status
import chatdev.sdk
from pathlib import Path
from chatdev import run_workflow


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

        code = str(result.output_dir / "code_workspace") if result.output_dir else str(generated_dir)

        return GenerationResult(
            status=Status.PASS if result.success else Status.FAIL,
            model=self._config.get("model"),
            code=code,
        )