import os
import json
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Unified master configuration for CodeGen, Minikube, and JMeter components."""
    def __init__(self, json_path: str | Path = "config.json"):
        self.base_dir = Path(__file__).resolve().parent
        
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                master_data = json.load(f)
        except FileNotFoundError:
            print(f"[WARN] Config file {json_path} not found. Using default dictionary keys.")
            master_data = {}

        # Phân tách cấu hình theo từng vùng dữ liệu
        agent_cfg = master_data.get("agent", {})
        minikube_cfg = master_data.get("minikube", {})
        jmeter_cfg = master_data.get("jmeter", {})

        # =====================================================================
        # 1. CORE & AGENT CONFIGURATION
        # =====================================================================
        self.prompt_name = agent_cfg.get("prompt_name", "prompt_v2_simplified.md")
        self.agent_name = agent_cfg.get("agent_name", "chatdev")
        self.api_base = agent_cfg.get("api_base", "https://ollama.com/v1")
        llm_raw = agent_cfg.get("llm", "qwen3.5:cloud")
        out = agent_cfg.get("out", "generated")

        self.pipeline_data_dir = self.base_dir / "data"
        self.prompts_dir = self.pipeline_data_dir / "prompts"
        self.config_dir = self.pipeline_data_dir / "config"
        self.output_dir = self.base_dir / out

        self.prompts_dir.mkdir(parents=True, exist_ok=True)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.prompt_path = self.prompts_dir / self.prompt_name
        self.agent_config_path = self.config_dir / f"{self.agent_name}.yaml"

        api_key = os.getenv("API_KEY")
        if not api_key:
            print("Error: API_KEY is missing. Please check your .env file.")
            exit(1)
        self.api_key = api_key

        if self.agent_name == "mini":
            self.llm = "ollama/" + llm_raw
        else:
            self.llm = llm_raw

        # =====================================================================
        # 2. MINIKUBE DEPLOY CONFIGURATION
        # =====================================================================
        app_dir_raw = minikube_cfg.get("app_dir")
        self.app_dir = Path(app_dir_raw) if app_dir_raw else self.output_dir
        
        self.manifest_file = minikube_cfg.get("manifest_file", "flask-k8s.yaml")
        self.image_name = minikube_cfg.get("image_name", "flask-app")
        
        self.manifest_dir = self.base_dir / "data" / "k8s_manifests"
        self.manifest_path = self.manifest_dir / self.manifest_file
        
        self.service_name = minikube_cfg.get("service_name", "flask-service")
        self.local_port = minikube_cfg.get("local_port", 8080)
        self.service_port = minikube_cfg.get("service_port", 5000)
        
        version_tag_raw = minikube_cfg.get("version_tag")
        self.version_tag = version_tag_raw if version_tag_raw else f"v_{int(time.time())}"
        self.full_image_tag = f"{self.image_name}:{self.version_tag}"

        # =====================================================================
        # 3. JMETER EVAL CONFIGURATION
        # =====================================================================
        self.target_host = jmeter_cfg.get("target_host", "localhost")
        self.target_port = jmeter_cfg.get("target_port", 8080)
        self.jmeter_xml = jmeter_cfg.get("jmeter_xml", "template.xml")
        self.jmeter_path = jmeter_cfg.get("jmeter_path", "jmeter")
        self.threads = jmeter_cfg.get("threads", 5)
        self.loops = jmeter_cfg.get("loops", 10)
        
        # Đổi tên biến thư mục kết quả jmeter để tách biệt với output_dir của agent codegen
        self.jmeter_output_dir = self.base_dir / "eval_results" / "jmeter"
        self.jmeter_output_dir.mkdir(parents=True, exist_ok=True)
        self.test_scenarios = self.base_dir / "data" / "jmeter_scenarios"
        
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.jmx_file = os.path.join(self.jmeter_output_dir, f"test_plan_{self.timestamp}.jmx")
        self.jtl_file = os.path.join(self.jmeter_output_dir, f"results_{self.timestamp}.jtl")
        self.report_dir = os.path.join(self.jmeter_output_dir, f"report_{self.timestamp}")
        self.log_file = os.path.join(self.jmeter_output_dir, f"log_{self.timestamp}.log")
        print(self.base_dir)