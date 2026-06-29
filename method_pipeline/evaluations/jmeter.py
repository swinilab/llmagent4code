import os
import subprocess
import csv
import time
import threading
from datetime import datetime
from pathlib import Path

class JMeterConfig:
    """Configuration holder for the test environment."""
    def __init__(self, 
                 target_host: str = "localhost", 
                 target_port: int = 8080,
                 jmeter_xml: str = "template.xml", 
                 jmeter_path: str = "jmeter",   
                 threads: int = 5, 
                 loops: int = 10,
                ):
        self.base_dir = Path(__file__).resolve().parent.parent
        
        self.output_dir = self.base_dir / "eval_results" / "jmeter"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.test_scenarios = self.base_dir / "data" / "jmeter_scenarios"
        
        self.target_host = target_host
        self.target_port = target_port
        self.jmeter_xml = jmeter_xml
        self.jmeter_path = jmeter_path
        self.threads = threads
        self.loops = loops
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        self.jmx_file = os.path.join(self.output_dir, f"test_plan_{self.timestamp}.jmx")
        self.jtl_file = os.path.join(self.output_dir, f"results_{self.timestamp}.jtl")
        self.report_dir = os.path.join(self.output_dir, f"report_{self.timestamp}")
        self.log_file = os.path.join(self.output_dir, f"log_{self.timestamp}.log")

class JMeterTestPlanBuilder:
    """Responsible for generating the JMeter XML (.jmx) file."""
    
    def __init__(self, config: JMeterConfig):
        self.config = config

    def generate(self) -> str:
        template_path = self.config.test_scenarios / self.config.jmeter_xml
        
        if not template_path.exists():
            raise FileNotFoundError(f"Không tìm thấy file template tại: {template_path}")
            
        with open(template_path, 'r', encoding='utf-8') as f:
            xml_template = f.read()
            
        xml_content = xml_template.format(
            host=self.config.target_host,
            port=self.config.target_port,
            threads=self.config.threads,
            loops=self.config.loops,
            jtl_file=self.config.jtl_file
        )
        
        return xml_content

class LiveProgressMonitor:
    """Monitors the .jtl file in real-time to output progress metrics."""
    def __init__(self, jtl_file: str, total_expected: int):
        self.jtl_file = jtl_file
        self.total_expected = total_expected
        self.stop_event = threading.Event()
        self.current_count = 0

    def start(self):
        self.monitor_thread = threading.Thread(target=self._tail_jtl)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

    def stop(self):
        self.stop_event.set()
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.join(timeout=2)
        print(f"\n[INFO] Finalized live progress tracking. Sent: {self.current_count}/{self.total_expected}")

    def _tail_jtl(self):
        while not os.path.exists(self.jtl_file) and not self.stop_event.is_set():
            time.sleep(0.3)

        try:
            with open(self.jtl_file, 'r', encoding='utf-8', errors='ignore') as f:
                f.readline()
                
                while not self.stop_event.is_set():
                    line = f.readline()
                    if not line:
                        time.sleep(0.1)
                        continue
                    
                    if line.strip():
                        self.current_count += 1
                        percentage = (self.current_count / self.total_expected) * 100
                        print(f"\r[PROGRESS] Sent Requests: {self.current_count}/{self.total_expected} ({percentage:.2f}%)", end="", flush=True)
        except Exception as e:
            print(f"\n[WARN] Error during live monitoring: {e}")
    
class JMeterMain:
    """Main Orchestrator class to manage the test lifecycle."""
    
    def __init__(self, config: JMeterConfig):
        self.config = config
        self.builder = JMeterTestPlanBuilder(config)
        self._ensure_output_dir()
        
        # Số lượng Sampler cố định trong template kịch bản (mặc định là 3: /, /items, /orders)
        self.num_samplers_in_template = 3 
        self.total_requests = self.config.threads * self.config.loops * self.num_samplers_in_template

    def _ensure_output_dir(self):
        if not os.path.exists(self.config.output_dir):
            os.makedirs(self.config.output_dir)
            print(f"[INFO] Created output directory: {self.config.output_dir}")

    def prepare_test_plan(self):
        """Writes the .jmx file to disk."""
        print(f"[INFO] Generating JMeter Test Plan: {self.config.jmx_file}")
        xml_content = self.builder.generate()
        with open(self.config.jmx_file, 'w', encoding='utf-8') as f:
            f.write(xml_content)
        print("[INFO] Test Plan generated successfully.")

    def run(self) -> bool:
        """Executes the JMeter CLI command and monitors progress."""
        cmd = [
            self.config.jmeter_path, 
            "-n", 
            "-t", self.config.jmx_file, 
            "-l", self.config.jtl_file,
            "-j", self.config.log_file
        ]
        
        print(f"[INFO] Running JMeter Command: {' '.join(cmd)}")
        print(f"[INFO] Target Total Requests: {self.total_requests} ({self.config.threads} threads x {self.config.loops} loops x {self.num_samplers_in_template} endpoints)")
        
        # Khởi chạy Monitor luồng nền
        monitor = LiveProgressMonitor(self.config.jtl_file, self.total_requests)
        monitor.start()

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Dừng monitor sau khi subprocess chạy xong
            monitor.stop()

            if result.returncode == 0:
                print("[SUCCESS] JMeter test execution completed.")
                return True
            else:
                print(f"[ERROR] JMeter failed with code {result.returncode}")
                print(f"STDERR: {result.stderr}")
                return False
        except FileNotFoundError:
            monitor.stop()
            print(f"[ERROR] JMeter not found at '{self.config.jmeter_path}'. Ensure it is installed and in PATH.")
            return False
        except Exception as e:
            monitor.stop()
            print(f"[ERROR] Unexpected error: {e}")
            return False

    def summarize_results(self):
        """Parses the .jtl CSV file to provide a simple summary."""
        if not os.path.exists(self.config.jtl_file):
            print("[WARN] Results file not found. Cannot summarize.")
            return

        total = 0
        errors = 0
        avg_time = 0
        
        try:
            with open(self.config.jtl_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    total += 1
                    if row.get('success', '').lower() == 'false':
                        errors += 1
                    try:
                        avg_time += int(row.get('elapsed', 0))
                    except (ValueError, TypeError):
                        pass
                
                if total > 0:
                    avg_time = avg_time / total
                    success_rate = ((total - errors) / total) * 100
                    
                    print("\n" + "="*30)
                    print("TEST SUMMARY")
                    print("="*30)
                    print(f"Total Requests Processed: {total}")
                    print(f"Errors:                  {errors}")
                    print(f"Success Rate:            {success_rate:.2f}%")
                    print(f"Avg Response:            {avg_time:.2f} ms")
                    print("="*30)
                else:
                    print("[WARN] No samples recorded in results file.")
                    
        except Exception as e:
            print(f"[ERROR] Could not parse results file: {e}")
            import traceback
            traceback.print_exc()

    def execute_full_cycle(self):
        """Convenience method to run the whole flow."""
        self.prepare_test_plan()
        success = self.run()
        if success:
            self.summarize_results()
        else:
            print("[ABORT] Skipping summary due to execution failure.")

if __name__ == "__main__":
    config = JMeterConfig(
        target_host="localhost",
        target_port=5000,
        jmeter_xml="template.jmx", 
        jmeter_path="jmeter",
        threads=500,
        loops=5
    )

    runner = JMeterMain(config)
    print(f"Starting Load Test against {config.target_host}:{config.target_port}...")
    runner.execute_full_cycle()