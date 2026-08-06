# tests/nfr/JmeterRunner.py
"""
JMeterRunner
============
Thin wrapper around the JMeter CLI (non-GUI mode).

Responsibilities:
  - Build the `jmeter -n -t ...` command from a dict of properties
    (already resolved from create_apis.json by the caller — this class
    never reads create_apis.json itself).
  - Execute JMeter as a subprocess and capture stdout/stderr.
  - Parse the resulting .jtl (JMeter XML results) file into a plain
    Python dict of aggregate metrics (p95, p99, error rate, etc.).

This class is intentionally "dumb": it does not know about NFR ids,
thresholds, or pass/fail logic. That logic belongs to NFRValidator.
Keeping this class narrow makes it independently testable and reusable
across different NFR checks (load test, spike test, etc.).
"""

from __future__ import annotations

import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from dataclasses import dataclass


class JMeterExecutionError(Exception):
    """Raised when the JMeter process itself fails to run
    (non-zero exit code, binary not found, timeout, etc.).
    This is distinct from a "failed" load test — a load test can finish
    successfully and still show a high error rate; that's a metrics
    problem, not an execution problem."""
    pass


@dataclass
class JMeterMetrics:
    """Aggregate metrics parsed from a single .jtl results file.
    Field names mirror what NFR checks typically compare against
    thresholds (p95/p99 latency, error rate, throughput)."""
    total_requests: int
    error_count: int
    error_rate: float | None
    p95_ms: float | None
    p99_ms: float | None
    avg_ms: float | None
    min_ms: float | None
    max_ms: float | None

    def to_dict(self) -> dict:
        return self.__dict__.copy()


class JMeterRunner:
    """
    Executes a .jmx test plan via JMeter's CLI and returns parsed metrics.

    Usage:
        runner = JMeterRunner()
        metrics = runner.run(
            jmx_file="jmeter/load_test.jmx",
            jmeter_props={"BASE_URL": "http://localhost:8000", "ORDER_PATH": "/api/v1/orders"},
            result_dir="reports/nfr/load_test",
        )
        # metrics["p95_ms"], metrics["error_rate"], ...

    Note on property naming:
    The keys in `jmeter_props` must exactly match the property names
    referenced inside the .jmx file via ${__P(KEY_NAME)}. This class does
    not validate that match — a mismatch will silently fall back to the
    .jmx file's own default value (if any), so keep names consistent
    between the caller (NFRValidator) and the .jmx test plan.
    """

    def __init__(self, jmeter_bin: str = "jmeter", default_timeout_s: int = 600):
        self.jmeter_bin = jmeter_bin
        self.default_timeout_s = default_timeout_s

    def run(
        self,
        jmx_file: str,
        jmeter_props: dict[str, str],
        result_dir: str,
        timeout_s: int | None = None,
    ) -> dict:
        """
        Run a JMeter test plan and return parsed aggregate metrics.

        Args:
            jmx_file: path to the .jmx test plan (fixed, reused across candidates).
            jmeter_props: values to inject via -J flags; keys must match
                ${__P(...)} placeholders used inside the .jmx file.
            result_dir: directory to write the .jtl results file and JMeter log into.
                Created if it doesn't exist.
            timeout_s: override the default subprocess timeout.

        Returns:
            dict of aggregate metrics (see JMeterMetrics fields).

        Raises:
            JMeterExecutionError: if the JMeter process exits non-zero,
                times out, or the binary can't be found.
        """
        Path(result_dir).mkdir(parents=True, exist_ok=True)
        jtl_path = f"{result_dir}/result.jtl"
        log_path = f"{result_dir}/jmeter.log"

        cmd = self._build_command(jmx_file, jmeter_props, jtl_path, log_path)

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_s or self.default_timeout_s,
            )
        except FileNotFoundError as e:
            raise JMeterExecutionError(
                f"JMeter binary '{self.jmeter_bin}' not found on PATH"
            ) from e
        except subprocess.TimeoutExpired as e:
            raise JMeterExecutionError(
                f"JMeter run timed out after {timeout_s or self.default_timeout_s}s"
            ) from e

        if proc.returncode != 0:
            raise JMeterExecutionError(
                f"JMeter exited with code {proc.returncode}\n"
                f"stdout: {proc.stdout[-2000:]}\n"
                f"stderr: {proc.stderr[-2000:]}"
            )

        return self._parse_jtl(jtl_path).to_dict()

    def _build_command(
        self,
        jmx_file: str,
        jmeter_props: dict[str, str],
        jtl_path: str,
        log_path: str,
    ) -> list[str]:
        """Assemble the JMeter CLI command.
        -n : non-GUI mode (required for CI/automated runs)
        -t : test plan file
        -l : results log file (.jtl, XML format by default)
        -j : JMeter's own engine log (separate from results)
        -J : injects a JMeter property, readable in the .jmx via ${__P(KEY)}
        """
        cmd = [
            self.jmeter_bin,
            "-n",
            "-t", jmx_file,
            "-l", jtl_path,
            "-j", log_path,
        ]
        for key, value in jmeter_props.items():
            cmd.append(f"-J{key}={value}")
        return cmd

    def _parse_jtl(self, jtl_path: str) -> JMeterMetrics:
        """
        Parse a JMeter .jtl (XML) results file into aggregate metrics.

        Expects the default XML output format (JMeter's default when
        jmeter.save.saveservice.output_format is unset or "xml").
        Each <httpSample> / <sample> element represents one request;
        's' attribute is the success flag ("true"/"false") and 't' is
        elapsed time in milliseconds.
        """
        if not Path(jtl_path).exists():
            raise JMeterExecutionError(f"Expected results file not found: {jtl_path}")

        tree = ET.parse(jtl_path)
        root = tree.getroot()

        latencies: list[int] = []
        error_count = 0

        # httpSample = single HTTP request; sample = generic/nested sample.
        # Both are collected since JMeter can emit either depending on sampler type.
        for sample in root.findall(".//httpSample") + root.findall(".//sample"):
            elapsed = sample.get("t")
            if elapsed is None:
                continue
            latencies.append(int(elapsed))
            if sample.get("s") != "true":
                error_count += 1

        total = len(latencies)
        if total == 0:
            # No samples parsed — likely a config error in the .jmx
            # (e.g. wrong placeholder name resolved to an invalid path).
            return JMeterMetrics(
                total_requests=0,
                error_count=0,
                error_rate=None,
                p95_ms=None,
                p99_ms=None,
                avg_ms=None,
                min_ms=None,
                max_ms=None,
            )

        latencies.sort()
        return JMeterMetrics(
            total_requests=total,
            error_count=error_count,
            error_rate=error_count / total,
            p95_ms=latencies[int(total * 0.95) - 1] if total > 0 else None,
            p99_ms=latencies[int(total * 0.99) - 1] if total > 0 else None,
            avg_ms=sum(latencies) / total,
            min_ms=latencies[0],
            max_ms=latencies[-1],
        )