import subprocess
import chatdev.sdk
import os
from pprint import pprint
from abc import ABC, abstractmethod
from chatdev import run_workflow, AgentConfig
from pathlib import Path
from config import Config
from concrete.agents.chat_dev import ChatDev
from concrete.agents.mini_swe_agent import MiniSweAgent

class BaseAgent(ABC):
    @abstractmethod
    def gen_code(self, config) -> bool:
        pass

class ChatDevAdapter(BaseAgent):
    def __init__(self):
        self.agent = ChatDev()

    def gen_code(self, config) -> bool:
        print("-> [Code] ChatDev is running")
        return self.agent.run(config)

class MiniSweAgentAdapter(BaseAgent):
    def __init__(self):
        self.agent = MiniSweAgent()

    def gen_code(self, config) -> bool:
        print("-> [Code] mini-swe-agent is running")
        return self.agent.run(config)

class AgentFactory:
    # Dictionary mapping between config and the corresponded class
    _AGENT_MAP = {
        "chatdev": ChatDevAdapter,
        "mini": MiniSweAgentAdapter
    }

    @classmethod
    def create_agent(cls, agent_name: str) -> BaseAgent:
        # Standardized agent name
        name_lower = agent_name.lower()
        
        if name_lower not in cls._AGENT_MAP:
            raise ValueError(f"Agent '{agent_name}' is not supported !")
            
        # init and return the agent class
        return cls._AGENT_MAP[name_lower]()
    
if __name__ == "__main__":
    print(os.getcwd())