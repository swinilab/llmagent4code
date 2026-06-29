import os
import subprocess
import time
import re
import threading
from pathlib import Path

class MinikubeDeployConfig:
    """Configuration holder for the packaging and deployment process on Minikube."""
    def __init__(self, 
                 app_dir: Path | None = None,
                 manifest_file: str = "flask-k8s.yaml", 
                 image_name: str = "flask-app",
                 version_tag: str | None = None,
                 local_port: int = 8080,
                 service_port: int = 5000,
                 service_name: str = "flask-service"):
        
        # Base setup pointing to generated folders
        self.base_dir = Path(__file__).resolve().parent.parent
        self.app_dir = Path(app_dir) if app_dir else self.base_dir / "generated"
        self.manifest_dir = self.base_dir / "data" / "k8s_manifests"
        self.manifest_path = self.manifest_dir / manifest_file
        
        self.image_name = image_name
        self.service_name = service_name
        
        # Port mapping configurations for port forwarding
        self.local_port = local_port
        self.service_port = service_port
        
        # If no tag is specified, generate a unique timestamp-based tag to bypass image cache
        self.version_tag = version_tag if version_tag else f"v_{int(time.time())}"
        self.full_image_tag = f"{self.image_name}:{self.version_tag}"

class MinikubeDeployer:
    """Manages the lifecycle of building images, updating manifests, and deploying to Minikube from WSL."""
    def __init__(self, config: MinikubeDeployConfig):
        self.config = config
        self.port_forward_proc = None

    def _get_minikube_docker_env(self) -> dict:
        """Extracts environment variables from 'minikube docker-env' to inject into subprocesses."""
        env = os.environ.copy()
        try:
            # Equivalent to evaluating $(minikube docker-env) in bash
            result = subprocess.run(["minikube", "docker-env", "--shell", "bash"], 
                                    capture_output=True, text=True, check=True)
            
            # Match all export KEY="VALUE" patterns
            matches = re.findall(r'export\s+(\w+)="([^"]+)"', result.stdout)
            for key, value in matches:
                env[key] = value
            return env
        except Exception as e:
            print(f"[ERROR] Failed to fetch Minikube docker environment: {e}")
            return env

    def build_image(self) -> bool:
        """Builds the Docker image directly inside Minikube's built-in Docker registry."""
        print(f"[INFO] Targeting Minikube Docker CLI. Building image: {self.config.full_image_tag}")
        
        if not (self.config.app_dir / "Dockerfile").exists():
            print(f"[ERROR] Dockerfile not found at: {self.config.app_dir}")
            return False

        cmd = ["docker", "build", "-t", self.config.full_image_tag, "."]
        env_minikube = self._get_minikube_docker_env()

        try:
            result = subprocess.run(cmd, cwd=str(self.config.app_dir), env=env_minikube, 
                                    capture_output=True, text=True)
            if result.returncode == 0:
                print(f"[SUCCESS] Successfully built {self.config.full_image_tag} inside Minikube.")
                return True
            else:
                print(f"[ERROR] Docker build failed.\nSTDERR: {result.stderr}")
                return False
        except Exception as e:
            print(f"[ERROR] Unexpected error during docker build: {e}")
            return False

    def update_manifest_image(self) -> bool:
        """Injects the newly generated image tag into the target Kubernetes manifest file."""
        if not self.config.manifest_path.exists():
            print(f"[ERROR] Kubernetes Manifest not found at: {self.config.manifest_path}")
            return False

        try:
            with open(self.config.manifest_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Regex pattern to locate 'image: <image_name>:<any_tag>' and swap the tag
            pattern = rf"(image:\s*{self.config.image_name}):\S+"
            new_content = re.sub(pattern, rf"\1:{self.config.version_tag}", content)

            with open(self.config.manifest_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print(f"[INFO] Updated manifest file with image version: {self.config.version_tag}")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to modify manifest YAML: {e}")
            return False

    def apply_manifest(self) -> bool:
        """Applies the declaration file into the Minikube cluster using kubectl."""
        print("[INFO] Applying Kubernetes manifests to Minikube...")
        cmd = ["kubectl", "apply", "-f", str(self.config.manifest_path)]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print("[SUCCESS] Kubernetes resources applied successfully.")
                return True
            else:
                print(f"[ERROR] Kubectl apply execution failed.\nSTDERR: {result.stderr}")
                return False
        except Exception as e:
            print(f"[ERROR] Internal exception executing kubectl apply: {e}")
            return False

    def wait_for_deployment(self, deployment_name: str = "flask-deployment", timeout_seconds: int = 120) -> bool:
        """Blocks execution until all replica pods in the deployment reach a Running/Ready state."""
        print(f"[INFO] Verifying deployment state. Waiting for pods under '{deployment_name}'...")
        cmd = ["kubectl", "rollout", "status", f"deployment/{deployment_name}", f"--timeout={timeout_seconds}s"]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print("[SUCCESS] All pods are running and stable. Ready for testing.")
                return True
            else:
                print(f"[WARN] Rollout status exceeded timeout limits or failed.\n{result.stderr}")
                return False
        except Exception as e:
            print(f"[ERROR] Exception monitoring deployment progress: {e}")
            return False

    def start_port_forward(self) -> bool:
        """Launches a background non-blocking port-forward pipeline from Host to Service."""
        print(f"[INFO] Spawning background process for Port Forwarding...")
        print(f"[INFO] Mapping local port http://localhost:{self.config.local_port} -> K8s service port {self.config.service_port}")
        
        cmd = [
            "kubectl", "port-forward", 
            f"svc/{self.config.service_name}", 
            f"{self.config.local_port}:{self.config.service_port}"
        ]

        try:
            # Popen spawns the process in the background without blocking the script execution
            self.port_forward_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            # Give the tunnel 2 seconds to establish network socket interfaces
            time.sleep(2)
            
            # Check if the process died immediately (e.g., Address already in use)
            if self.port_forward_proc.poll() is not None:
                _, stderr = self.port_forward_proc.communicate()
                print(f"[ERROR] Port forward failed to start immediately.\nSTDERR: {stderr}")
                return False
                
            print(f"[SUCCESS] Port forward tunnel opened actively on PID: {self.port_forward_proc.pid}")
            return True
        except Exception as e:
            print(f"[ERROR] Exception while spawning port forward instance: {e}")
            return False

    def stop_port_forward(self):
        """Terminates the active background port forward tunnel to free local port allocation."""
        if self.port_forward_proc and self.port_forward_proc.poll() is None:
            print(f"[INFO] Terminating port-forward background process (PID: {self.port_forward_proc.pid})...")
            self.port_forward_proc.terminate()
            self.port_forward_proc.wait()
            print("[SUCCESS] Port forward tunnel closed successfully.")
    
    def stop_minikube(self) -> bool:
        """Executes 'minikube stop' to safely power down the cluster local instance."""
        print("[INFO] Initiating Minikube cluster shutdown...")
        cmd = ["minikube", "stop"]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print("[SUCCESS] Minikube cluster has been stopped safely.")
                return True
            else:
                print(f"[ERROR] Failed to stop Minikube.\nSTDERR: {result.stderr}")
                return False
        except Exception as e:
            print(f"[ERROR] Exception occurred during Minikube shutdown: {e}")
            return False

    def execute_deploy_flow(self) -> bool:
        """Main function orchestrating the complete deploying phase."""
        if not self.build_image():
            return False
        if not self.update_manifest_image():
            return False
        if not self.apply_manifest():
            return False
        if not self.wait_for_deployment():
            return False
        
        # Establish the static route path before handing over control to testing suites
        return self.start_port_forward()
    
if __name__ == "__main__":
    # Custom test configuration block
    conf = MinikubeDeployConfig(local_port=8080)
    deployer = MinikubeDeployer(conf)
    try:
        success = deployer.execute_deploy_flow()
        if success:
            print("[INFO] Cluster setup complete. Press Ctrl+C to stop port forwarding and exit.")
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        print("\n[INFO] Script interrupted by user.")
    finally:
        # Guarantee network cleanup even if execution fails
        deployer.stop_port_forward()