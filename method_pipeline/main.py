from config import Config
from agents.mini_swe_agent_caller import MiniSweAgent
from agents.chat_dev_caller import ChatDev


CONFIG = {
    "prompt_name": "prompt.md",
    "agent_name": "chatdev",
    "api_base": "https://ollama.com/v1",
    "llm": "gemma4:cloud"
}

def main():
    print("--- LLM-Agent4CodeGen v0.1 ---")

    mini = MiniSweAgent()
    chatdev = ChatDev()

    config = Config(
        CONFIG["prompt_name"],
        CONFIG["agent_name"],
        CONFIG["api_base"],
        CONFIG["llm"]
    )

    # Invoke your agent caller utilizing the encapsulated instance paths
    # success = mini.run(config)
    success = chatdev.run(config)

    if success:
        print("Pipeline code generation phase completed successfully.")
    else:
        print("Pipeline halted due to agent execution error.")


if __name__ == "__main__":
    main()