import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    """The main configuration of the pipeline."""
    def __init__(self, prompt_name: str, agent_name: str, api_base: str, llm: str):
        # set up dirs
        self.base_dir = Path(__file__).resolve().parent
        self.pipeline_data_dir = self.base_dir / "data"
        self.prompts_dir = self.pipeline_data_dir / "prompts"
        self.config_dir = self.pipeline_data_dir / "config"
        self.output_dir = self.base_dir / "generated" / "chatdev-300626"

        self.prompts_dir.mkdir(parents=True, exist_ok=True)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # set up file PATHs
        self.prompt_path = self.prompts_dir / prompt_name
        self.agent_config_path = self.config_dir / f"{agent_name}.yaml"

        self.api_base = api_base
        api_key = os.getenv("API_KEY")
        if not api_key:
            print("Error: API_KEY is missing. Please check your .env file.")
            exit(1)
        self.api_key = api_key
        if agent_name == "mini":
            self.llm = "ollama/" + llm
        else:
            self.llm = llm