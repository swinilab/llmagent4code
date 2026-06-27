import os
from pathlib import Path
from dotenv import load_dotenv
import yaml

load_dotenv()

class Config:
    """The main configuration of the pipeline."""
    def __init__(self, prompt_name: str, agent_name: str, api_base: str, llm: str):
        # set up dirs
        self.base_dir = Path(__file__).resolve().parent
        self.pipeline_data_dir = self.base_dir / "data"
        self.prompts_dir = self.pipeline_data_dir / "prompts"
        self.config_dir = self.pipeline_data_dir / "config"
        self.output_dir = self.pipeline_data_dir / "generated1"

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
        self.llm = llm


if __name__ == "__main__":
    con = Config("prompt.md", "mini")
    print(con.base_dir)
    print(con.prompts_dir)
    print(con.config_dir)
    print(con.output_dir)
    print(con.prompt_path)
