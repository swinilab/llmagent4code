import chatdev.sdk
import os
from pathlib import Path
from dotenv import load_dotenv
from chatdev import run_workflow, AgentConfig
from config import Config
from pprint import pprint

class ChatDev():
    def __init__(self) -> None:
        pass

    def run(self, config: Config):
        prompt_text = config.prompt_path.read_text(encoding="utf-8")
        chatdev.sdk.OUTPUT_ROOT = Path(config.output_dir)

        result = run_workflow(
            yaml_file=config.agent_config_path,
            task_prompt=prompt_text,
            variables= {
                "BASE_URL": config.api_base,
                "API_KEY": config.api_key,
                "MODEL_NAME": config.llm
            },
        )
        pprint(result)