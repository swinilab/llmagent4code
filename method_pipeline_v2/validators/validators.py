"""
validators/real_validators.py
──────────────────────────────
Real implementations of ICompilabilityValidator and IFunctionalValidator.
"""
from __future__ import annotations

import subprocess
import httpx
import os, re
from pathlib import Path
import json

from interfaces.base import (
    ICompilabilityValidator,
    IFunctionalValidator,
    Status,
    TestResult,
    ValidationResult,
    GenerationResult
)
from validators.tests.CustomerTestGroup import CustomerTestGroup
from validators.tests.InvoiceTestGroup import InvoiceTestGroup
from validators.tests.OrderTestGroup import OrderTestGroup
from validators.tests.PaymentTestGroup import PaymentTestGroup
from validators.tests.ProductTestGroup import ProductTestGroup


class CompilabilityValidator(ICompilabilityValidator):
    """
    Real Compilability Validator:
    - Reads the startup command from /start_command.txt
    - Executes it via subprocess (e.g. starting a Docker container)
    - Captures exit codes, stdout, and stderr
    """
    def __init__(self, config: dict | None = None) -> None:
        config = config or {}
        self._generated_dir = Path(
            config.get("agent", {}).get("generated_dir", "generated")
        )
        self._start_command_file = config.get("validator", {}).get("start_command_file", "start_command.txt")

    def _clean_logs(self, raw_text: str) -> str:
        if not raw_text:
            return ""
        lines = raw_text.splitlines()
        clean_lines = [
            line for line in lines 
            if line.strip() and not line.strip().startswith('#')
        ]
        return "\n".join(clean_lines)

    def validate(self, gen_result: str, code: str) -> ValidationResult:
        # workdir = self._generated_dir / gen_result.output_dir / "code_workspace"
        workdir = Path(code)

        try:
            command = Path(os.path.join(
                workdir,
                self._start_command_file
            )).read_text().strip()
        except FileNotFoundError:
            return ValidationResult(
                stage="compilability",
                status=Status.FAIL,
                message=f"Start command file not found: {self._start_command_file}",
                details={"error": "FileNotFoundError"},
            )
        except Exception as e:
            return ValidationResult(
                stage="compilability",
                status=Status.FAIL,
                message=f"Failed to read command file: {e}",
                details={"error": str(e)},
            )

        try:
            # THUẬT TOÁN ÉP CHỜ:
            # Chạy lệnh trong foreground (không dùng cờ -d của docker).
            # Ép quá trình chờ tối đa 10 giây (timeout=10).
            # Nếu là web server (FastAPI), nó sẽ block luồng mãi mãi -> văng lỗi TimeoutExpired.
            # TimeoutExpired trong trường hợp này lại là TIN TỐT (nghĩa là server không bị crash).
            
            process = subprocess.run(
                command,
                cwd=workdir,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60 # Quan trọng: Chờ 10 giây xem app có crash không
            )
            
            # Nếu lệnh kết thúc sớm hơn 10 giây và trả về lỗi (!= 0) -> Chắc chắn app đã crash
            if process.returncode != 0:
                return ValidationResult(
                    status=Status.FAIL, 
                    stage="compilability",
                    message="Runtime error or crash detected during startup", 
                    details={"stderr": process.stderr, "stdout": process.stdout}
                )
            
            # (Trường hợp lệnh là script chạy ngắn, chạy xong thành công trả về 0)
            return ValidationResult(
                status=Status.PASS, 
                stage="compilability",
                message="Executed successfully without crashing",
                details={}
            )

        except subprocess.TimeoutExpired as e:
            # 1. DỌN DẸP CONTAINER: 
            # Bắt buộc phải tắt container đang chạy ngầm để giải phóng Port cho lần kiểm tra sau
            subprocess.run(
                "docker compose down", 
                cwd=workdir, 
                shell=True, 
                capture_output=True
            )
            
            # 2. KHỞI TẠO ĐÚNG THAM SỐ:
            # Tạm thời gọi bằng positional arguments (bỏ chữ passed=, message=)
            # LƯU Ý: Đổi thứ tự/số lượng biến dưới đây cho khớp với interfaces/base.py của bạn
            return ValidationResult(
                status=Status.PASS,                                                    
                stage="Compilability",
                message="Server started and remained stable (Timeout reached)", 
                details={}
            )
        except Exception as e:
            return ValidationResult(
                status=Status.FAIL, 
                stage="compilability",
                message=f"Validator internal error: {str(e)}", 
                details={"stderr": str(e)}
            )

class FunctionalValidator(IFunctionalValidator):
    """
    Real Functional Validator:
    - Fires live HTTP requests using httpx against the running container
    - Validates actual HTTP status codes against expected status codes
    """
    def __init__(
        self, 
        endpoints: list[dict] | None = None, 
        config: dict | None = None
    ) -> None:
        config = config or {}
        self._base_url = config.get("validator", {}).get("base_url", "http://localhost:8000")
        self._timeout = config.get("validator", {}).get("timeout", 10.0)
        self._generated_dir = Path(
            config.get("agent", {}).get("generated_dir", "generated")
        )
        # Default to /start_command.txt as requested, but allow override via config
        self._start_command_file = config.get("validator", {}).get("start_command_file", "start_command.txt")

    def _resolve_create_api_path(
        self,
        create_api_paths: dict,
        entity_key: str,
        default_path: str,
    ) -> str:
        """Resolve the create-endpoint path for an entity from create_apis.json,
        falling back to a sensible default if the key/path is missing or null."""
        entry = create_api_paths.get(entity_key)
        if entry is not None and entry.get("path") is not None:
            return entry["path"]
        return default_path

    def validate(self, generation_result: GenerationResult, code: str) -> ValidationResult:
        workdir = os.path.join(
                self._generated_dir,
                generation_result.output_dir,
                "code_workspace")
        create_api_paths = dict()
        with open(os.path.join(workdir, 'create_apis.json'), 'r', encoding='utf-8') as file:
            create_api_paths = json.load(file)
        
        results = list[TestResult]()

        customer_create_api = self._resolve_create_api_path(
            create_api_paths, "customer", "/api/v1/customers"
        )
        customer_group = CustomerTestGroup(api=self._base_url + customer_create_api)
        results.extend(customer_group.run_all())

        product_create_api = self._resolve_create_api_path(
            create_api_paths, "product", "/api/v1/products"
        )
        product_group = ProductTestGroup(api=self._base_url + product_create_api)
        results.extend(product_group.run_all())

        order_create_api = self._resolve_create_api_path(
            create_api_paths, "order", "/api/v1/orders"
        )
        order_group = OrderTestGroup(api=self._base_url + order_create_api)
        results.extend(order_group.run_all())

        payment_create_api = self._resolve_create_api_path(
            create_api_paths, "payment", "/api/v1/payments"
        )
        payment_group = PaymentTestGroup(api=self._base_url + payment_create_api)
        results.extend(payment_group.run_all())

        invoice_create_api = self._resolve_create_api_path(
            create_api_paths, "invoice", "/api/v1/invoices"
        )
        invoice_group = InvoiceTestGroup(api=self._base_url + invoice_create_api)
        results.extend(invoice_group.run_all())

        failed = [r for r in results if r.result == False]
        if failed:
            return ValidationResult(
                stage="functional",
                status=Status.FAIL,
                message=f"{len(failed)} of {len(results)} HTTP test(s) failed.",
                details={"results": results, "failed": failed},
            )
            
        return ValidationResult(
            stage="functional",
            status=Status.PASS,
            message=f"All {len(results)} HTTP functional tests passed.",
            details={"results": results},
        )

if __name__ == "__main__":
    """
    Quick manual smoke-test entry point.
 
    Assumes the OMS app is ALREADY RUNNING at http://localhost:8000 (started
    manually by you) - this block does NOT start/stop any process, it just
    drives FunctionalValidator.validate() against it and prints a readable
    PASS/FAIL report.
 
    Usage (run from the project root, NOT from inside validators/ - this file
    uses package-relative imports like `from interfaces.base import ...`,
    so it must be invoked as a module):
        python -m validators.real_validators
 
    Running `python validators/real_validators.py` directly will fail with
    `ModuleNotFoundError: No module named 'interfaces'`.
 
    It expects (and will auto-create if missing) a create_apis.json at:
        generated/run1/code_workspace/create_apis.json
    Edit CREATE_APIS_JSON below if your endpoint paths differ.
    """
    import sys
 
    CREATE_APIS_JSON = {
        "customer": {"method": "POST", "path": "/api/v1/customers"},
        "product":  {"method": "POST", "path": "/api/v1/products"},
        "order":    {"method": "POST", "path": "/api/v1/orders"},
        "payment":  {"method": "POST", "path": "/api/v1/payments"},
        "invoice":  {"method": "POST", "path": "/api/v1/invoices"},
    }
 
    GENERATED_DIR = "generated"
    OUTPUT_DIR = "sdk-test-hope"
    BASE_URL = "http://localhost:8000"

    workdir = os.path.join(GENERATED_DIR, OUTPUT_DIR, "code_workspace")
    os.makedirs(workdir, exist_ok=True)

    create_apis_path = os.path.join(workdir, "create_apis.json")
    if not os.path.exists(create_apis_path):
        with open(create_apis_path, "w", encoding="utf-8") as f:
            json.dump(CREATE_APIS_JSON, f, indent=2, ensure_ascii=False)
        print(f"[setup] Wrote default create_apis.json to {create_apis_path}")

    start_command_path = os.path.join(workdir, "start_command.txt")
    if not os.path.exists(start_command_path):
        with open(start_command_path, "w", encoding="utf-8") as f:
            f.write("echo 'app already running - nothing to start'\n")
 
    config = {
        "validator": {
            "base_url": BASE_URL,
            "timeout": 10.0,
            "start_command_file": "start_command.txt",
        },
        "agent": {
            "generated_dir": GENERATED_DIR,
        },
    }
 
    generation_result = GenerationResult(output_dir=OUTPUT_DIR, model="ok", completion=True)
 
    validator = FunctionalValidator(config=config)
    result = validator.validate(generation_result=generation_result, code="unused")
 
    print("=" * 70)
    print(f"STAGE   : {result.stage}")
    print(f"STATUS  : {result.status}")
    print(f"MESSAGE : {result.message}")
    print("=" * 70)
 
    all_results = result.details.get("results", [])
    failed_results = result.details.get("failed", [])
    passed_count = len(all_results) - len(failed_results)
    print(f"\nPassed: {passed_count} / {len(all_results)}\n")
 
    if failed_results:
        print("Failed test cases:")
        print("-" * 70)
        for r in failed_results:
            print(f"[FAIL] {r.testcase_id}: {r.message}")
        print("-" * 70)
    else:
        print("All test cases passed.")
 
    report = {
        "stage": result.stage,
        "status": str(result.status),
        "message": result.message,
        "total": len(all_results),
        "passed": passed_count,
        "failed": len(failed_results),
        "results": [
            {"testcase_id": r.testcase_id, "result": r.result, "message": r.message}
            for r in all_results
        ],
    }
    report_path = Path("functional_test_report.json")
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nFull report written to {report_path.resolve()}")
 
    sys.exit(0 if result.status == Status.PASS else 1)