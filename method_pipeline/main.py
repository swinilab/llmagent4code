from config import Config
from agents.mini_swe_agent_caller import MiniSweAgent
from agents.chat_dev_caller import ChatDev


CONFIG = {
    "prompt_name": "prompt_orderman_order_pipeline.md",
    "agent_name": "mini",
    "api_base": "https://ollama.com/v1",
    "llm": "ollama/qwen3.5:cloud"
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

    success = mini.run(config)
    # success = chatdev.run(config)

    if success:
        print("Pipeline code generation phase completed successfully.")
    else:
        print("Pipeline halted due to agent execution error.")


if __name__ == "__main__":
    main()