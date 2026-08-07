from __future__ import annotations
import subprocess
import os, re
from pathlib import Path
from datetime import datetime
import json
from interfaces.base import (
    IFunctionalValidator,
    Status,
    TestResult,
    ValidationResult,
    GenerationResult
)
from validators.tests.test_groups.CustomerTestGroup import CustomerTestGroup
from validators.tests.test_groups.InvoiceTestGroup import InvoiceTestGroup
from validators.tests.test_groups.OrderTestGroup import OrderTestGroup
from validators.tests.test_groups.PaymentTestGroup import PaymentTestGroup
from validators.tests.test_groups.ProductTestGroup import ProductTestGroup

# group name -> (TestGroup class, entity key in create_apis.json, default create path)
TEST_GROUPS = {
    "customer": (CustomerTestGroup, "customer", "/apiX/vX/customers"),
    "product":  (ProductTestGroup,  "product",  "/apiX/vX/products"),
    "order":    (OrderTestGroup,    "order",    "/apiX/vX/orders"),
    "payment":  (PaymentTestGroup,  "payment",  "/apiX/vX/payments"),
    "invoice":  (InvoiceTestGroup,  "invoice",  "/apiX/vX/invoices"),
}

class FunctionalValidator(IFunctionalValidator):
    """
    Real Functional Validator:
    - Fires live HTTP requests using httpx against the running container
    - Validates actual HTTP status codes against expected status codes
    - Exports the full per-testcase results to a JSON report and returns a
      per-test-group summary so the pipeline's .txt report can stay concise
    """
    def __init__(
        self,
        endpoints: list[dict] | None = None,
        config: dict | None = None
    ) -> None:
        config = config or {}
        self._base_url = config.get("validator", {}).get("base_url", "http://localhost:8000")
        self._timeout = config.get("validator", {}).get("timeout", 10.0)
        # Default to /start_command.txt as requested, but allow override via config
        self._start_command_file = config.get("validator", {}).get("start_command_file", "start_command.txt")
        self._report_dir = config.get("output", {}).get("report_dir", "reports/")
        self._generated_dir = Path(
            config.get("agent", {}).get("generated_dir", "generated")
        )

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

    def _write_json_report(
        self,
        status: Status,
        message: str,
        results: list[TestResult],
        summary: list[dict],
    ) -> str:
        os.makedirs(self._report_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(self._report_dir, f"functional_test_report_{timestamp}.json")

        payload = {
            "stage": "functional",
            "status": status.name,
            "message": message,
            "total": len(results),
            "passed": len([r for r in results if r.result]),
            "failed": len([r for r in results if not r.result]),
            "summary": summary,
            "results": [
                {"testcase_id": r.testcase_id, "result": r.result, "message": r.message}
                for r in results
            ],
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        return path

    def validate(self, generation_result: GenerationResult) -> ValidationResult:
        workdir = Path(os.path.join(
            self._generated_dir,
            generation_result.code
        ))
        with open(os.path.join(workdir, 'create_apis.json'), 'r', encoding='utf-8') as file:
            create_api_paths = json.load(file)

        results: list[TestResult] = []
        summary: list[dict] = []

        for group_name, (group_cls, entity_key, default_path) in TEST_GROUPS.items():
            api_path = self._resolve_create_api_path(create_api_paths, entity_key, default_path)
            group_results = group_cls(api=self._base_url + api_path).run_all()
            results.extend(group_results)

            failed_count = sum(1 for r in group_results if not r.result)
            summary.append({
                "group": group_name,
                "total": len(group_results),
                "passed": len(group_results) - failed_count,
                "failed": failed_count,
            })

        case_specific_message = ""
        for result in results:
            case_specific_message += f"""testcase_id:        {result.testcase_id}\nresult:             {"PASS" if result.result else "FALSE"}\nmessage:            {result.message}\n\n"""

        failed_count = sum(1 for r in results if not r.result)
        status = Status.FAIL if failed_count else Status.PASS
        message = (
            f"{failed_count} of {len(results)} HTTP test(s) failed."
            if failed_count
            else f"All {len(results)} HTTP functional tests passed."
        )

        report_path = self._write_json_report(status, message, results, summary)

        return ValidationResult(
            stage="functional",
            status=status,
            message=message + "\n" + case_specific_message,
            details={
                "total": len(results),
                "passed": len(results) - failed_count,
                "failed": failed_count,
                "summary": summary,
                "report_path": report_path,
            },
        )
