from config import Config
from components.agent import AgentFactory
from components.deploy import MinikubeDeployerAdapter
from components.evaluate import JMeterEvaluatorAdapter

def main():
    print("--- LLM-Agent4CodeGen v0.1 ---")
    
    config = Config("config.json")
    
    agent = AgentFactory.create_agent(config.agent_name)
    deployer = MinikubeDeployerAdapter(config)
    evaluator = JMeterEvaluatorAdapter(config)
    
    print("========== Code Generation Phase ==========")
    if not agent.gen_code(config):
        return

    # print("========== Minikube Deploying Phase ==========")
    # if not deployer.deploy():
    #     return

    # try:
    #     print("========== Evaluation Phase ==========")
    #     evaluator.evaluate()
    # finally:
    #     deployer.cleanup()

if __name__ == "__main__":
    main()