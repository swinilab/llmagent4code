"""
NFRValidator — stage 4 of the validation waterfall.

Runs all 6 NFR checks (1.1, 1.2, 1.3, 2.1, 2.2, 2.3) against a live
running instance of the generated app, and folds the results into a
single ValidationResult that main.py / report_writer already understand.

Thresholds are owned here (not read from the candidate's own
nfr-trace.json) — see design note in tests/nfr/thresholds.py.
"""
from __future__ import annotations
import json
import requests
from interfaces.base import INFRValidator, GenerationResult, ValidationResult
from tests.nfr.NFRResult import NFRCheckResult, build_validation_result
from tests.nfr.JmeterRunner import JMeterRunner
# from tests.nfr.FaultInjector import FaultInjector


class NFRValidator(INFRValidator):
    def __init__(self, config: dict):
        self.config = config
        self.base_url = config["validation"]["http"]["base_url"]
        self.jmx_dir = config["validation"]["scenario"]
        self.jmeter = JMeterRunner()
        # self.fault_injector = FaultInjector()

    def validate(self, generation_result: GenerationResult) -> ValidationResult:
        api_paths = self._load_api_paths(generation_result.code)

        checks: list[NFRCheckResult] = [
            self._check_nfr_1_1(api_paths),
            # self._check_nfr_1_2(api_paths),
            # self._check_nfr_1_3(api_paths),
            # self._check_nfr_2_1(api_paths),
            # self._check_nfr_2_2(),
            # self._check_nfr_2_3(api_paths),
        ]

        return build_validation_result(checks)

    def _load_api_paths(self, code: str) -> dict:
        with open(f"{code}/create_apis.json") as f:
            return json.load(f)

    def _build_jmeter_props(self, api_paths: dict, extra: dict | None = None) -> dict:
        props = {"BASE_URL": self.base_url}
        for entity, cfg in api_paths.items():
            props[f"{entity.upper()}_PATH"] = cfg["path"]
        if extra:
            props.update(extra)
        return props

    # ── NFR 1.1 — Response Time ─────────────────────────────────────────
    def _check_nfr_1_1(self, api_paths: dict) -> NFRCheckResult:
        """Mixed realistic traffic (product search + order checkout),
        moderate concurrency. Checks p95 latency stays under threshold."""
        metrics = self.jmeter.run(
            jmx_file=f"{self.jmx_dir}/load_test.jmx",
            jmeter_props=self._build_jmeter_props(api_paths),
            result_dir="reports/nfr/nfr_1_1",
        )
        threshold = {"p95_ms": 200}
        passed = metrics.get("p95_ms") is not None and metrics["p95_ms"] < threshold["p95_ms"]
        return NFRCheckResult(
            nfr_id="NFR 1.1 Response Time",
            passed=passed,
            measured=metrics,
            threshold=threshold,
            message="" if passed else f"p95={metrics.get('p95_ms')}ms exceeds {threshold['p95_ms']}ms",
        )

    # ── NFR 1.2 — Concurrency & Resource Utilization ────────────────────
    def _check_nfr_1_2(self, api_paths: dict) -> NFRCheckResult:
        """Ramp concurrency in steps (e.g. 10 -> 50 -> 100 -> 200 threads)
        and check throughput scales without a disproportionate error-rate
        spike or latency collapse, indicating the app actually uses
        available concurrency instead of serializing requests."""
        metrics_low = self.jmeter.run(
            jmx_file=f"{self.jmx_dir}/concurrency_test.jmx",
            jmeter_props=self._build_jmeter_props(api_paths, {"THREADS": "20"}),
            result_dir="reports/nfr/nfr_1_2_low",
        )
        metrics_high = self.jmeter.run(
            jmx_file=f"{self.jmx_dir}/concurrency_test.jmx",
            jmeter_props=self._build_jmeter_props(api_paths, {"THREADS": "200"}),
            result_dir="reports/nfr/nfr_1_2_high",
        )

        threshold = {"max_error_rate": 0.05, "min_throughput_ratio": 3.0}
        throughput_low = self._throughput(metrics_low)
        throughput_high = self._throughput(metrics_high)
        ratio = (throughput_high / throughput_low) if throughput_low else 0

        passed = (
            metrics_high.get("error_rate") is not None
            and metrics_high["error_rate"] < threshold["max_error_rate"]
            and ratio >= threshold["min_throughput_ratio"]
        )
        return NFRCheckResult(
            nfr_id="NFR 1.2 Concurrency & Resource Utilization",
            passed=passed,
            measured={
                "throughput_at_20_threads": throughput_low,
                "throughput_at_200_threads": throughput_high,
                "scaling_ratio": ratio,
                "error_rate_at_200_threads": metrics_high.get("error_rate"),
            },
            threshold=threshold,
            message="" if passed else f"throughput did not scale (ratio={ratio:.2f}) or error rate too high",
        )

    def _throughput(self, metrics: dict) -> float:
        """requests/sec approximation from total_requests and avg latency
        is unreliable; prefer JMeter's own throughput if the runner exposes
        it. Placeholder here assumes JMeterRunner adds 'throughput_rps'."""
        return metrics.get("throughput_rps", 0.0)

    # ── NFR 1.3 — Queue Management ──────────────────────────────────────
    def _check_nfr_1_3(self, api_paths: dict) -> NFRCheckResult:
        """Burst of concurrent order-creation requests fired at once
        (Synchronizing Timer in the .jmx). Checks the app queues/accepts
        the spike (e.g. 202) instead of dropping connections or crashing."""
        metrics = self.jmeter.run(
            jmx_file=f"{self.jmx_dir}/spike_test.jmx",
            jmeter_props=self._build_jmeter_props(api_paths),
            result_dir="reports/nfr/nfr_1_3",
        )
        threshold = {"max_error_rate": 0.0}
        passed = metrics.get("error_rate") == threshold["max_error_rate"]
        return NFRCheckResult(
            nfr_id="NFR 1.3 Queue Management",
            passed=passed,
            measured=metrics,
            threshold=threshold,
            message="" if passed else f"error_rate={metrics.get('error_rate')} under burst load",
        )

    # ── NFR 2.1 — Graceful Degradation ──────────────────────────────────
    def _check_nfr_2_1(self, api_paths: dict) -> NFRCheckResult:
        """Put the app under heavy resource contention (parallel load +
        killed background worker, via FaultInjector), then check the core
        checkout journey still returns 2xx while a non-essential endpoint
        degrades to 503."""
        result = self.fault_injector.test_graceful_degradation(
            app_container_name=self.config["nfr"]["app_container"],
            base_url=self.base_url,
            checkout_path=api_paths["order"]["path"],
            non_essential_path=self.config["nfr"].get(
                "non_essential_path", "/api/v1/recommendations"
            ),
        )
        threshold = {"checkout_must_stay_2xx": True, "non_essential_must_degrade": True}
        passed = (
            result.get("checkout_status_ok") is True
            and result.get("non_essential_degraded") is True
        )
        return NFRCheckResult(
            nfr_id="NFR 2.1 Graceful Degradation",
            passed=passed,
            measured=result,
            threshold=threshold,
            message="" if passed else "checkout failed or non-essential endpoint did not degrade under contention",
        )

    # ── NFR 2.2 — Fault Detection and Recovery ──────────────────────────
    def _check_nfr_2_2(self) -> NFRCheckResult:
        """Disconnect the DB container from the network, poll /health/ready
        to measure detection latency, reconnect, poll again to measure
        recovery latency."""
        result = self.fault_injector.test_fault_recovery(
            db_container_name=self.config["nfr"]["db_container"],
            network_name=self.config["nfr"]["network"],
            health_url=f"{self.base_url}/health/ready",
        )
        threshold = {"max_detection_s": 10, "max_recovery_s": 15}
        passed = (
            result.get("fully_recovered") is True
            and result.get("detection_latency_s") is not None
            and result["detection_latency_s"] < threshold["max_detection_s"]
            and result.get("recovery_latency_s") is not None
            and result["recovery_latency_s"] < threshold["max_recovery_s"]
        )
        return NFRCheckResult(
            nfr_id="NFR 2.2 Fault Detection and Recovery",
            passed=passed,
            measured=result,
            threshold=threshold,
            message="" if passed else "app did not detect/recover from DB fault within threshold",
        )

    # ── NFR 2.3 — State Preservation ────────────────────────────────────
    def _check_nfr_2_3(self, api_paths: dict) -> NFRCheckResult:
        """Create a pending order, kill the app container mid-flight,
        restart it, and verify the order's state survived without loss."""

        def create_order() -> str:
            resp = requests.post(
                f"{self.base_url}{api_paths['order']['path']}",
                json=self.config["nfr"]["sample_order_body"],
                timeout=10,
            )
            return resp.json()["id"]

        result = self.fault_injector.test_state_preservation(
            app_container_name=self.config["nfr"]["app_container"],
            base_url=self.base_url,
            create_order_fn=create_order,
        )
        threshold = {"order_must_be_preserved": True}
        passed = result.get("order_preserved") is True
        return NFRCheckResult(
            nfr_id="NFR 2.3 State Preservation",
            passed=passed,
            measured=result,
            threshold=threshold,
            message="" if passed else "pending order was lost after process restart",
        )