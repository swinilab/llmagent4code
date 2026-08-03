"""Concurrent HTTP workload generation and latency measurement.

Latency and status codes are measured client-side, here, rather than taken from
anything the application reports. This is the "k6/JMeter" row of the external
evidence table, implemented in-process so that a run needs no extra tooling and
observations stay attached to the individual requests that produced them.

Percentiles use nearest-rank on the raw sample, with no interpolation and no
discarding of outliers -- a rejected request that took four seconds must show up
in p95, because hiding it would hide exactly the failure mode we are testing for.
"""

from __future__ import annotations

import asyncio
import math
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

import httpx

from . import trace


@dataclass(frozen=True)
class Response:
    """One completed (or failed) request."""

    status: int | None          # None when the request never produced a response
    elapsed_ms: float
    body: Any = None
    headers: Mapping[str, str] = field(default_factory=dict)
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.status is not None and 200 <= self.status < 300

    def error_code(self) -> str | None:
        """Pull error.code out of a controlled failure body.

        This is how ASR-A1 is told apart from ASR-A3: both may answer 503, but
        only one of them is allowed to call itself DEPENDENCY_TIMEOUT.
        """
        if isinstance(self.body, dict):
            err = self.body.get("error")
            if isinstance(err, dict):
                code = err.get("code")
                return str(code) if code is not None else None
        return None


@dataclass
class Workload:
    """Aggregate view of a batch of responses."""

    responses: list[Response]

    @property
    def count(self) -> int:
        return len(self.responses)

    def status_distribution(self) -> dict[str | int, int]:
        return dict(Counter(r.status if r.status is not None else "transport_error" for r in self.responses))

    def with_status(self, *statuses: int) -> list[Response]:
        return [r for r in self.responses if r.status in statuses]

    def successes(self) -> list[Response]:
        return [r for r in self.responses if r.ok]

    def success_rate(self) -> float:
        return len(self.successes()) / self.count if self.count else 0.0

    def error_rate(self) -> float:
        return 1.0 - self.success_rate()

    def unhandled_500s(self) -> int:
        """Count 500s that are NOT a declared controlled transaction failure.

        A 500 carrying TRANSACTION_FAILED is a designed response in ASR-A4. Any
        other 500 is the unhandled kind the measures require to be zero.
        """
        return sum(
            1
            for r in self.responses
            if r.status == 500 and r.error_code() != "TRANSACTION_FAILED"
        )

    def p95_ms(self) -> float:
        return self.percentile_ms(95)

    def percentile_ms(self, pct: float, subset: Sequence[Response] | None = None) -> float:
        sample = subset if subset is not None else self.responses
        values = sorted(r.elapsed_ms for r in sample)
        if not values:
            return float("nan")
        rank = max(1, math.ceil(pct / 100.0 * len(values)))
        return values[min(rank, len(values)) - 1]

    def max_ms(self) -> float:
        return max((r.elapsed_ms for r in self.responses), default=float("nan"))

    def hanging(self, threshold_s: float) -> int:
        return sum(1 for r in self.responses if r.elapsed_ms > threshold_s * 1000)


class HttpHarness:
    def __init__(self, base_url: str, timeout_s: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s

    # ── single request ────────────────────────────────────────────────────

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any = None,
        headers: Mapping[str, str] | None = None,
        timeout_s: float | None = None,
    ) -> Response:
        with httpx.Client(timeout=timeout_s or self.timeout_s) as client:
            return _perform_sync(client, self.base_url, method, path, json_body, headers)

    def get(self, path: str, **kw: Any) -> Response:
        return self.request("GET", path, **kw)

    def post(self, path: str, **kw: Any) -> Response:
        return self.request("POST", path, **kw)

    # ── concurrent workload ───────────────────────────────────────────────

    def run_concurrent(
        self,
        method: str,
        path: str,
        *,
        total: int,
        concurrency: int,
        headers: Mapping[str, str] | None = None,
        json_body: Any = None,
        timeout_s: float | None = None,
    ) -> Workload:
        """Issue `total` requests, at most `concurrency` in flight.

        Used for ASR-P1's 1,000-read throughput phase. A semaphore bounds
        in-flight work so the client cannot itself become the bottleneck being
        measured.
        """
        return asyncio.run(
            self._run_concurrent(
                method, path, total, concurrency, headers, json_body, timeout_s
            )
        )

    def run_simultaneous(
        self,
        method: str,
        path: str,
        *,
        total: int,
        headers: Mapping[str, str] | None = None,
        json_body: Any = None,
        timeout_s: float | None = None,
    ) -> Workload:
        """Fire `total` requests at once, each on its own connection.

        This is the ASR-P2 stimulus, and it is the one workload where the
        client's own pooling would corrupt the measurement. Sharing a pool
        across two hundred simultaneous requests makes them queue for a
        connection, and that wait lands inside the measured time -- so a server
        rejecting in nine milliseconds is recorded as rejecting in seconds, and
        a correct immediate-refusal implementation looks exactly like the
        bounded queue this tactic is defined against.

        One shared client is used, but with a connection pool larger than the
        burst so no request ever waits for a slot, and with keep-alive disabled
        so a finished request cannot hand its connection to a waiting one and
        serialise the two. Giving each request its own client was tried and is
        far worse -- two hundred simultaneous client constructions cost more
        than the measurement itself.
        """
        return asyncio.run(
            self._run_burst(method, path, total, headers, json_body, timeout_s)
        )

    async def _run_burst(
        self,
        method: str,
        path: str,
        total: int,
        headers: Mapping[str, str] | None,
        json_body: Any,
        timeout_s: float | None,
    ) -> Workload:
        limits = httpx.Limits(
            max_connections=total + 64,
            max_keepalive_connections=0,
        )
        async with httpx.AsyncClient(
            timeout=timeout_s or self.timeout_s, limits=limits
        ) as client:
            gathered = await asyncio.gather(
                *(
                    _perform_async(client, self.base_url, method, path, json_body, headers)
                    for _ in range(total)
                )
            )
        return Workload(list(gathered))

    def run_sequential(
        self,
        method: str,
        path: str,
        *,
        total: int,
        headers: Mapping[str, str] | None = None,
        pause_s: float = 0.0,
    ) -> Workload:
        """Issue requests one at a time, optionally paced.

        ASR-A3 spreads 600 reads across a 60-second outage; the point there is
        continued availability, not throughput.
        """
        out: list[Response] = []
        with httpx.Client(timeout=self.timeout_s) as client:
            for _ in range(total):
                out.append(_perform_sync(client, self.base_url, method, path, None, headers))
                if pause_s:
                    time.sleep(pause_s)
        return Workload(out)

    async def _run_concurrent(
        self,
        method: str,
        path: str,
        total: int,
        concurrency: int,
        headers: Mapping[str, str] | None,
        json_body: Any,
        timeout_s: float | None,
    ) -> Workload:
        limits = httpx.Limits(max_connections=concurrency + 16, max_keepalive_connections=concurrency)
        sem = asyncio.Semaphore(concurrency)
        async with httpx.AsyncClient(timeout=timeout_s or self.timeout_s, limits=limits) as client:

            async def one() -> Response:
                async with sem:
                    return await _perform_async(client, self.base_url, method, path, json_body, headers)

            gathered = await asyncio.gather(*(one() for _ in range(total)))
        return Workload(list(gathered))


# ── request execution ─────────────────────────────────────────────────────
#
# Both paths record elapsed time around the whole call including transport
# errors, so a connection that is dropped after three seconds is counted as a
# three-second request rather than vanishing from the sample.


def _decode(resp: httpx.Response) -> Any:
    try:
        return resp.json()
    except ValueError:
        return resp.text


def _perform_sync(
    client: httpx.Client,
    base: str,
    method: str,
    path: str,
    json_body: Any,
    headers: Mapping[str, str] | None,
) -> Response:
    url = f"{base}{path}"
    start = time.perf_counter()
    try:
        resp = client.request(method, url, json=json_body, headers=dict(headers or {}))
        elapsed = (time.perf_counter() - start) * 1000
        out = Response(resp.status_code, elapsed, _decode(resp), dict(resp.headers))
    except httpx.RequestError as exc:
        out = Response(None, (time.perf_counter() - start) * 1000, error=str(exc))
    _log(method, url, json_body, headers, out)
    return out


async def _perform_async(
    client: httpx.AsyncClient,
    base: str,
    method: str,
    path: str,
    json_body: Any,
    headers: Mapping[str, str] | None,
) -> Response:
    url = f"{base}{path}"
    start = time.perf_counter()
    try:
        resp = await client.request(method, url, json=json_body, headers=dict(headers or {}))
        elapsed = (time.perf_counter() - start) * 1000
        out = Response(resp.status_code, elapsed, _decode(resp), dict(resp.headers))
    except httpx.RequestError as exc:
        out = Response(None, (time.perf_counter() - start) * 1000, error=str(exc))
    _log(method, url, json_body, headers, out)
    return out


def _log(
    method: str,
    url: str,
    json_body: Any,
    headers: Mapping[str, str] | None,
    resp: Response,
) -> None:
    """Hand the completed exchange to the tracer.

    Recorded after the fact rather than around the call so the timing above
    stays exactly what it was: the measurement must not include the cost of
    writing the log line.
    """
    trace.record_request(
        method,
        url,
        request_body=json_body,
        headers=headers,
        status=resp.status,
        elapsed_ms=resp.elapsed_ms,
        response_body=resp.body,
        response_headers=resp.headers,
        error=resp.error,
    )