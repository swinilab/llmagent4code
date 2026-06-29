from config import Config
from agents.mini_swe_agent_caller import MiniSweAgent
from agents.chat_dev_caller import ChatDev
from evaluations.jmeter import JMeterConfig, JMeterMain
from evaluations.minikube import MinikubeDeployConfig, MinikubeDeployer

CONFIG = {
    "prompt_name": "prompt_v2_simplified.md",
    "agent_name": "chatdev",
    "api_base": "https://ollama.com/v1",
    "llm": "qwen3.5:cloud"
}

def main():
    print("--- LLM-Agent4CodeGen v0.1 ---")
    print("========== Code Generation Phase ==========")
    mini = MiniSweAgent()
    chatdev = ChatDev()
    config = Config(
        CONFIG["prompt_name"],
        CONFIG["agent_name"],
        CONFIG["api_base"], 
        CONFIG["llm"]
    )

    # success = mini.run(config)
    success = chatdev.run(config)
    # success = True

    if success:
        print("Pipeline code generation phase completed successfully.")
    else:
        print("Pipeline halted due to agent execution error.")

    exit(1)
    
    print("========== Minikube Deploying Phase ==========")
    deploy_config = MinikubeDeployConfig(
        image_name="flask-app",
        manifest_file="flask-k8s.yaml",
        local_port=8080 
    )
    deployer = MinikubeDeployer(deploy_config)
    
    deploy_success = deployer.execute_deploy_flow()
    
    if not deploy_success:
        print("[ABORT] Pipeline stopped due to deployment failure.")
        return

    try:
        print("========== Evaluation Phase ==========")
        print("1. JMeter Testing")
        jmeter_config = JMeterConfig(
            target_host="localhost",
            target_port=8080, # Point to the forwarded local port
            jmeter_xml="template.jmx", 
            jmeter_path="jmeter",
            threads=10,
            loops=5
        )
        jmeter = JMeterMain(jmeter_config)
        jmeter.execute_full_cycle()

    finally:
        print("========== Pipeline Cleanup Phase ==========")
        # 1. Terminate the background port forward tunnel to release port 8080
        deployer.stop_port_forward()
        
        # 2. Shut down the Minikube cluster node instance to save RAM/CPU
        deployer.stop_minikube()


if __name__ == "__main__":
    main()