"""Application-reported counters, treated as supplementary evidence.

Everything here is self-reported by the system under test, so it is the weakest
class of evidence the study uses. It is collected because some measures are
specified in terms of these counters, but no scenario passes on these numbers
alone: each one is paired with an external observation that would contradict a
fabricated counter.

The pairings, spelled out:

  db_product_reads_total          <-> pg_stat_user_tables scan delta
  db_product_read_attempts_total  <-> HTTP status and elapsed time
  requests_rejected_total         <-> observed count of 429/503 responses
  timeouts_total                  <-> client-side elapsed time
  transaction_rollbacks_total     <-> persisted row state read over SQL
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import httpx

REQUIRED_KEYS = (
    "cache_hits_total",
    "cache_misses_total",
    "db_product_reads_total",
    "db_product_read_attempts_total",
    "requests_accepted_total",
    "requests_rejected_total",
    "timeouts_total",
    "retry_attempts_total",
    "transaction_rollbacks_total",
)


class MetricsContractError(RuntimeError):
    """The metrics endpoint does not satisfy its declared schema.

    This makes dependent scenarios NOT_EXERCISABLE rather than FAIL: we cannot
    conclude a tactic is absent from an inability to measure it.
    """


@dataclass(frozen=True)
class Metrics:
    values: Mapping[str, int]

    def __getitem__(self, key: str) -> int:
        return self.values[key]

    def delta(self, earlier: "Metrics") -> dict[str, int]:
        return {k: self.values[k] - earlier.values.get(k, 0) for k in self.values}

    def cache_hit_rate(self) -> float:
        hits = self.values.get("cache_hits_total", 0)
        misses = self.values.get("cache_misses_total", 0)
        total = hits + misses
        return hits / total if total else 0.0


class AppMetrics:
    def __init__(self, base_url: str, timeout_s: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s

    def read(self) -> Metrics:
        with httpx.Client(timeout=self.timeout_s) as client:
            resp = client.get(f"{self.base_url}/internal/metrics")
        if resp.status_code != 200:
            raise MetricsContractError(f"/internal/metrics returned HTTP {resp.status_code}")
        try:
            body = resp.json()
        except ValueError as exc:
            raise MetricsContractError("/internal/metrics did not return JSON") from exc
        if not isinstance(body, dict):
            raise MetricsContractError("/internal/metrics must return a JSON object")

        missing = [k for k in REQUIRED_KEYS if k not in body]
        if missing:
            raise MetricsContractError(f"/internal/metrics is missing keys: {missing}")
        non_int = [k for k in REQUIRED_KEYS if not isinstance(body[k], int) or isinstance(body[k], bool)]
        if non_int:
            raise MetricsContractError(f"/internal/metrics keys are not integers: {non_int}")

        return Metrics({k: int(body[k]) for k in REQUIRED_KEYS})

    def reset(self) -> None:
        """Clear counters, cache and injected-fault state between runs."""
        with httpx.Client(timeout=self.timeout_s) as client:
            resp = client.post(f"{self.base_url}/internal/test/reset")
        if resp.status_code != 204:
            raise MetricsContractError(
                f"/internal/test/reset returned HTTP {resp.status_code}, expected 204"
            )

    def reachable_during_fault(self) -> bool:
        """Check the observation path still answers while a fault is active.

        The specification requires the observation paths to stay servable under
        every condition it exercises, so failing this *during* an injected fault
        is a defect in the application, not merely an inconvenience for us --
        it is asserted as such by the scenarios, producing FAIL rather than
        NOT_EXERCISABLE.

        The distinction matters and is easy to get backwards. Metrics that are
        unreachable before any fault is applied mean we never had the ability to
        measure, which is NOT_EXERCISABLE. Metrics that were reachable and then
        disappeared once the database went away mean the application routed its
        own observability through the dependency it was supposed to survive
        without -- an observed failure of the graceful-degradation contract.
        """
        try:
            with httpx.Client(timeout=self.timeout_s) as client:
                return client.get(f"{self.base_url}/internal/metrics").status_code == 200
        except httpx.RequestError:
            return False

    def health_reachable(self, path: str = "/health/live") -> tuple[bool, int | None]:
        """Probe a health path, returning reachability and status separately.

        /health/ready is expected to report unready during an outage, so a
        non-200 there is correct behaviour; what is not permitted is failing to
        answer at all. Callers need both facts to tell those apart.
        """
        try:
            with httpx.Client(timeout=self.timeout_s) as client:
                return True, client.get(f"{self.base_url}{path}").status_code
        except httpx.RequestError:
            return False, None