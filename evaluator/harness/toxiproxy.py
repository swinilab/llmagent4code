"""Toxiproxy control for database fault injection.

The evaluator never edits the generated application. Both availability faults it
needs -- slow database and absent database -- are produced here, by manipulating
the proxy the application already routes its PostgreSQL traffic through.

Toxiproxy state is also external evidence in its own right: it tells us the
outage really happened, independently of anything the application reports.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
from typing import Iterator

import httpx

from . import trace


class ToxiproxyError(RuntimeError):
    """Raised when the proxy is missing or misconfigured.

    This is deliberately distinct from a scenario failure. A broken proxy means
    the scenario could not be exercised at all, which is NOT_EXERCISABLE, not
    FAIL -- the distinction the study depends on.
    """


@dataclass(frozen=True)
class ProxyState:
    name: str
    listen: str
    upstream: str
    enabled: bool


class Toxiproxy:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 8474,
        timeout: float = 5.0,
        api_port_in_container: int = 8474,
    ):
        self._base = f"http://{host}:{port}"
        # Toxiproxy refuses API requests whose Host header does not match the
        # address it believes it is serving -- protection against DNS rebinding.
        # When the API is published on a shifted host port so the stack can run
        # alongside another one, every request would otherwise arrive claiming
        # a port Toxiproxy never bound, and be answered 403. Sending the
        # in-container address satisfies the check without weakening it.
        self._client = httpx.Client(
            base_url=self._base,
            timeout=timeout,
            headers={"Host": f"localhost:{api_port_in_container}"},
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "Toxiproxy":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ── inspection ────────────────────────────────────────────────────────

    def state(self, name: str = "postgres") -> ProxyState:
        try:
            resp = self._client.get(f"/proxies/{name}")
        except httpx.RequestError as exc:
            raise ToxiproxyError(f"Toxiproxy API unreachable at {self._base}: {exc}") from exc
        if resp.status_code == 404:
            raise ToxiproxyError(
                f"proxy {name!r} does not exist; the deployment contract requires it"
            )
        resp.raise_for_status()
        body = resp.json()
        return ProxyState(
            name=body["name"],
            listen=body["listen"],
            upstream=body["upstream"],
            enabled=body["enabled"],
        )

    def verify_contract(self, name: str, expected_upstream: str) -> None:
        """Confirm the application really is talking through the proxy.

        An application wired straight to db:5432 would sail through every
        availability scenario without implementing anything, because our faults
        would miss it entirely. Checking the upstream is what stops that.
        """
        st = self.state(name)
        if st.upstream != expected_upstream:
            raise ToxiproxyError(
                f"proxy {name!r} upstream is {st.upstream!r}, expected {expected_upstream!r}"
            )

    # ── fault injection ───────────────────────────────────────────────────

    def _delete_toxic(self, proxy: str, toxic: str) -> None:
        resp = self._client.delete(f"/proxies/{proxy}/toxics/{toxic}")
        if resp.status_code not in (204, 404):
            resp.raise_for_status()

    @contextlib.contextmanager
    def latency(self, ms: int, proxy: str = "postgres", jitter_ms: int = 0) -> Iterator[None]:
        """Add downstream latency for the duration of the block.

        Applied downstream (database -> application) so that the application's
        own read waits on it, which is the path ASR-A1's timeout must cover.
        """
        toxic = "evaluator_latency"
        self._delete_toxic(proxy, toxic)  # tolerate leftovers from a crashed run
        resp = self._client.post(
            f"/proxies/{proxy}/toxics",
            json={
                "name": toxic,
                "type": "latency",
                "stream": "downstream",
                "toxicity": 1.0,
                "attributes": {"latency": ms, "jitter": jitter_ms},
            },
        )
        resp.raise_for_status()
        trace.fault("injecting latency into", proxy, f"+{ms}ms downstream (jitter {jitter_ms}ms)")
        try:
            yield
        finally:
            self._delete_toxic(proxy, toxic)
            trace.fault("removing latency from", proxy, "normal")

    @contextlib.contextmanager
    def outage(self, proxy: str = "postgres") -> Iterator[None]:
        """Disable the proxy, simulating a fully unreachable database.

        Disabling the proxy severs established connections as well as refusing
        new ones, which is what makes this a genuine outage rather than a
        connection-pool exhaustion test.
        """
        self.set_enabled(proxy, False)
        try:
            yield
        finally:
            self.set_enabled(proxy, True)

    def set_enabled(self, proxy: str, enabled: bool) -> None:
        resp = self._client.post(f"/proxies/{proxy}", json={"enabled": enabled})
        resp.raise_for_status()
        trace.fault("db proxy", proxy, "ON (reachable)" if enabled else "OFF (outage)")

    def reset(self) -> None:
        """Remove every toxic and re-enable every proxy.

        Called between scenarios so a fault injected by one can never leak into
        the next and be misread as that scenario's own failure.
        """
        resp = self._client.post("/reset")
        resp.raise_for_status()