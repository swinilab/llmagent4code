from __future__ import annotations
import subprocess
import os, re
from pathlib import Path
import json
from interfaces.base import (
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
            create_api_paths, "customer", "/apiX/vX/customers"
        )
        customer_group = CustomerTestGroup(api=self._base_url + customer_create_api)
        results.extend(customer_group.run_all())

        product_create_api = self._resolve_create_api_path(
            create_api_paths, "product", "/apiX/vX/products"
        )
        product_group = ProductTestGroup(api=self._base_url + product_create_api)
        results.extend(product_group.run_all())

        order_create_api = self._resolve_create_api_path(
            create_api_paths, "order", "/apiX/vX/orders"
        )
        order_group = OrderTestGroup(api=self._base_url + order_create_api)
        results.extend(order_group.run_all())

        payment_create_api = self._resolve_create_api_path(
            create_api_paths, "payment", "/apiX/vX/payments"
        )
        payment_group = PaymentTestGroup(api=self._base_url + payment_create_api)
        results.extend(payment_group.run_all())

        invoice_create_api = self._resolve_create_api_path(
            create_api_paths, "invoice", "/apiX/vX/invoices"
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
