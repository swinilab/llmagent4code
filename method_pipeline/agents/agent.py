from abc import ABC, abstractmethod
from pathlib import Path
from config import Config

# class Agent(ABC):
#     def __init__(self, api_base: str, api_key: str, model_name: str):
#         self.api_base = api_base
#         self.model_name = model_name
#         self.api_key = api_key

#     @abstractmethod
#     def run(self, prompt_path: Path, out_dir: Path, config_path: Path) -> bool:
#         """
#         Abstract method that subclasses must implement.
#         """
#         pass

class Agent(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def run(self, config: Config):
        """
        Abstract method that subclasses must implement.
        """
        pass