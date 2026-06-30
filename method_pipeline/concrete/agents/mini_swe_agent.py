import os
import subprocess
from pathlib import Path
from config import Config

class MiniSweAgent():
    def __init__(self) -> None:
        pass

    def run(self, config: Config):
        """Executes mini-swe-agent inside the output directory"""

        if not config.prompt_path.exists():
            print(f"Error: Prompt file not found at {config.prompt_path}")
            return False

        if not config.agent_config_path.exists():
            print(f"Error: Mini's config file not found at {config.agent_config_path}")
            return False

        try:
            prompt_text = config.prompt_path.read_text(encoding="utf-8")
        except IOError as e:
            print(f"Failed to read prompt file: {e}")
            return False

        print(f"Starting agent at: {config.output_dir.name}")

        command = [
            "uv",
            "run",
            "mini-swe-agent",
            "--config",
            str(config.agent_config_path),
            "--task",
            prompt_text,
            "--model",
            config.llm,
            "--yolo",
            "--exit-immediately",
        ]

        try:
            current_env = os.environ.copy()

            result = subprocess.run(
                command,
                check=True,
                text=True,
                # capture_output=True,
                env=current_env,
                cwd=str(config.output_dir),
            )
            print("Agent completed successfully.")
            print("Agent Stdout Logs:")
            print(result.stdout)
            return True

        except subprocess.CalledProcessError as e:
            print(f"Agent execution failed with exit code {e.returncode}")
            print("Error Logs:")
            print(e.stderr)
            return False
        except FileNotFoundError:
            print(
                "Error: 'mini-swe-agent' CLI command not found. Ensure it is active."
            )
            return False