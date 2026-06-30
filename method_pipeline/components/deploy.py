from abc import ABC, abstractmethod
from config import Config
from concrete.deploy.minikube import MinikubeDeployer

class BaseDeployer(ABC):
    @abstractmethod
    def deploy(self) -> bool:
        pass

    @abstractmethod
    def cleanup(self) -> None:
        pass

class MinikubeDeployerAdapter(BaseDeployer):
    def __init__(self, config: Config):
        self.config = config
        self.deployer = MinikubeDeployer(self.config)

    def deploy(self) -> bool:
        print("-> [Deploy] Activating Minikube...")
        return self.deployer.execute_deploy_flow()

    def cleanup(self) -> None:
        print("-> [Cleanup] Cleaning Minikube's leftover...")
        # 1. Terminate background port forward tunnel
        self.deployer.stop_port_forward()
        # 2. Shut down Minikube cluster instance
        self.deployer.stop_minikube()