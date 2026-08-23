from __future__ import annotations
import os
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
from validators.tests.seed_context import build_seed_context, SeedContext

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
        http_config = config.get("validation", {}).get("http", {})
        self._base_url = http_config.get("base_url", "http://localhost:8000")
        self._timeout = http_config.get("timeout_seconds", 10.0)
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
        seed_warnings: list[str],
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
            "seed_warnings": seed_warnings,
            "summary": summary,
            "results": [
                {
                    "testcase_id": r.testcase_id,
                    "result": r.result,
                    "method": r.method,
                    "url": r.url,
                    "expected_status": r.expected_status,
                    "actual_status": r.actual_status,
                    "request_body": r.request_body,
                    "response_body": r.response_body,
                }
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

        workflow_api_paths: dict = {}
        workflow_apis_file = os.path.join(workdir, 'workflow_apis.json')
        if os.path.exists(workflow_apis_file):
            with open(workflow_apis_file, 'r', encoding='utf-8') as file:
                workflow_api_paths = json.load(file)

        api_paths = {
            entity_key: self._resolve_create_api_path(create_api_paths, entity_key, default_path)
            for _, entity_key, default_path in TEST_GROUPS.values()
        }

        try:
            seed = build_seed_context(self._base_url, api_paths, workflow_api_paths, self._timeout)
        except Exception as exc:
            seed = SeedContext(warnings=[f"seed setup phase crashed: {exc}"])

        for warning in seed.warnings:
            print(f"[FunctionalValidator] seed setup warning: {warning}")

        group_seed_kwargs = {
            "customer": {"seed_customer_id": seed.customer_id or ""},
            "product": {"seed_product_id": seed.product_id},
            "order": {
                "seed_customer_id": seed.customer_id,
                "seed_product_id": seed.product_id,
                "seed_invoice_id": seed.invoice_id,
                "seed_order_placed_id": seed.order_placed_id,
                "seed_order_with_invoice_id": seed.order_invoiced_id,
            },
            "payment": {
                "seed_order_invoiced_id": seed.order_invoiced_id,
                "seed_order_placed_id": seed.order_placed_id,
                "seed_invoice_total_amount": seed.invoice_total_amount,
            },
            "invoice": {
                "seed_order_accepted_id": seed.order_accepted_id,
                "seed_order_placed_id": seed.order_placed_id,
                "seed_order_accepted_total_amount": seed.order_total_amount,
            },
        }

        results: list[TestResult] = []
        summary: list[dict] = []

        for group_name, (group_cls, entity_key, default_path) in TEST_GROUPS.items():
            api_path = api_paths[entity_key]
            kwargs = group_seed_kwargs.get(group_name, {})
            group_results = group_cls(api=self._base_url + api_path, **kwargs).run_all()
            results.extend(group_results)

            failed_count = sum(1 for r in group_results if not r.result)
            summary.append({
                "group": group_name,
                "total": len(group_results),
                "passed": len(group_results) - failed_count,
                "failed": failed_count,
            })

        failed_count = sum(1 for r in results if not r.result)
        status = Status.FAIL if failed_count else Status.PASS
        message = (
            f"{failed_count} of {len(results)} HTTP test(s) failed."
            if failed_count
            else f"All {len(results)} HTTP functional tests passed."
        )

        report_path = self._write_json_report(status, message, results, summary, seed.warnings)

        return ValidationResult(
            stage="functional",
            status=status,
            message=message,
            details={
                "total": len(results),
                "passed": len(results) - failed_count,
                "failed": failed_count,
                "summary": summary,
                "report_path": report_path,
            },
        )
