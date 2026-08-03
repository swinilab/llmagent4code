"""Live console trace and durable per-request log.

Two audiences, one source of events.

The console stream is for a human watching a run: it says which scenario is
executing, what stimulus was applied, what was expected of each probe and what
came back. Without it a sixty-second outage scenario is a blank terminal, and a
failure discovered afterwards in the JSON report gives no clue which of the
dozen requests inside the run went wrong.

The JSONL file is for the evaluator afterwards: every HTTP request and response
issued by the harness, with body, headers, status, latency and the step it
belonged to. That is what makes a result auditable -- an assertion saying
"expected UNAVAILABLE, observed None" can be traced back to the exact response
that produced it, months later, without re-running anything.

The tracer is a module-level singleton on purpose. Requests originate deep
inside HttpHarness, several layers below any scenario, and threading a logger
through every call site would change signatures everywhere for no benefit. The
context that a request belongs to is carried in a contextvar instead, so the
concurrent workloads (ASR-P1, ASR-P2) label their requests correctly without
locking.
"""

from __future__ import annotations

import contextlib
import json
import sys
import threading
import time
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

# Which scenario/run/step the code is currently inside. Read by the HTTP layer
# when it records a request, so no caller has to pass it down.
_scope: ContextVar[dict[str, Any]] = ContextVar("trace_scope", default={})

# Bodies can be large -- a product list, a stack trace, an HTML error page. The
# full body is rarely what makes a failure understandable, and unbounded bodies
# turn the log into something no editor will open.
_MAX_BODY_CHARS = 2000
_MAX_CONSOLE_CHARS = 160


@dataclass
class Tracer:
    """Collects events; writes them to a file and optionally to the console.

    Disabled by default so importing the harness (as the unit tests do) has no
    side effects. `configure` turns it on for a real evaluation run.
    """

    path: Path | None = None
    console: bool = False
    verbose_requests: bool = False
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _fh: Any = None
    _counts: dict[str, int] = field(default_factory=dict)

    # ── lifecycle ─────────────────────────────────────────────────────────

    def open(self) -> None:
        if self.path is None or self._fh is not None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open("a", encoding="utf-8")

    def close(self) -> None:
        if self._fh is not None:
            self._fh.close()
            self._fh = None

    @property
    def enabled(self) -> bool:
        return self._fh is not None or self.console

    # ── event emission ────────────────────────────────────────────────────

    def emit(self, kind: str, **fields: Any) -> None:
        """Append one structured event to the log file.

        Never raises: a full disk or an un-encodable body must not abort an
        evaluation that is otherwise producing valid measurements.
        """
        if self._fh is None:
            return
        record = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "monotonic": round(time.monotonic(), 4),
            "kind": kind,
            **_scope.get(),
            **fields,
        }
        line = json.dumps(record, default=str)
        with self._lock:
            self._counts[kind] = self._counts.get(kind, 0) + 1
            try:
                self._fh.write(line + "\n")
                self._fh.flush()  # a crashed run must still leave a readable log
            except Exception:  # noqa: BLE001 - logging must never break a run
                pass

    def say(self, text: str, indent: int = 0) -> None:
        """Print one console line, if the console stream is on."""
        if self.console:
            print(" " * indent + text, flush=True)

    def counts(self) -> dict[str, int]:
        return dict(self._counts)


_tracer = Tracer()


def tracer() -> Tracer:
    return _tracer


def configure(path: Path | None, console: bool = True, verbose_requests: bool = False) -> Tracer:
    """Point the singleton at a log file and enable console output."""
    _tracer.path = path
    _tracer.console = console
    _tracer.verbose_requests = verbose_requests
    _tracer.open()
    return _tracer


# ── scope ─────────────────────────────────────────────────────────────────


@contextlib.contextmanager
def scope(**fields: Any) -> Iterator[None]:
    """Label every event raised inside the block.

    Nested scopes merge, so a request inside `step("writes")` inside
    `scenario("ASR-A3", run=2)` carries all three labels.
    """
    token = _scope.set({**_scope.get(), **fields})
    try:
        yield
    finally:
        _scope.reset(token)


def current_scope() -> dict[str, Any]:
    return dict(_scope.get())


# ── the narration API used by gates and scenarios ─────────────────────────


@contextlib.contextmanager
def phase(title: str, **fields: Any) -> Iterator[None]:
    """A named block of work -- a gate, or a scenario run."""
    _tracer.say(f"\n=== {title} ===")
    _tracer.emit("phase_start", title=title, **fields)
    started = time.monotonic()
    try:
        yield
    finally:
        _tracer.emit(
            "phase_end", title=title, duration_s=round(time.monotonic() - started, 2), **fields
        )


@contextlib.contextmanager
def step(name: str, detail: str = "", indent: int = 2) -> Iterator[None]:
    """One observable action within a scenario, e.g. 'writes during outage'.

    Requests issued inside are tagged with the step name in the log file, which
    is what lets the evaluator ask "what did the writes actually return?"
    without reading the surrounding code.
    """
    line = f"- {name}" + (f": {detail}" if detail else "")
    _tracer.say(line, indent)
    _tracer.emit("step", name=name, detail=detail)
    with scope(step=name):
        yield


def fault(action: str, target: str, state: str, **fields: Any) -> None:
    """Record a fault-injection change -- the stimulus half of the evidence.

    Printed prominently because it is the single most useful line for reading a
    trace: everything after it happened under that condition.
    """
    _tracer.say(f"  * {action} {target}: {state}", 0)
    _tracer.emit("fault", action=action, target=target, state=state, **fields)


def expectation(what: str, expected: Any, actual: Any, passed: bool, note: str = "") -> None:
    """Report one expected-vs-observed comparison as it is decided."""
    mark = "ok" if passed else "FAIL"
    line = f"    {what}: {mark} (expected {expected}, got {actual})"
    if note and not passed:
        line += f"  <- {note}"
    _tracer.say(line)
    _tracer.emit(
        "expectation", what=what, expected=str(expected), actual=str(actual),
        passed=passed, note=note,
    )


def note(text: str, **fields: Any) -> None:
    """Free-form observation worth seeing in the stream and keeping in the log."""
    _tracer.say(f"    {text}")
    _tracer.emit("note", text=text, **fields)


def assertions(items: Any) -> None:
    """Echo a finished assertion list through `expectation`.

    Scenarios build their assertions at the end, after all the measurement is
    done; this replays them so the console shows the verdict for each one
    instead of a bare PASS/FAIL for the run.
    """
    for a in items:
        expectation(a.name, a.expected, a.actual, a.passed, a.note)


# ── HTTP recording, called from the client layer ──────────────────────────


def record_request(
    method: str,
    url: str,
    *,
    request_body: Any = None,
    headers: Any = None,
    status: int | None = None,
    elapsed_ms: float = 0.0,
    response_body: Any = None,
    response_headers: Any = None,
    error: str | None = None,
) -> None:
    """Log one completed request/response pair.

    Called for every request the harness makes, including those inside the
    concurrent workloads -- that is deliberate. A 200-request burst produces 200
    lines, which is exactly what is needed to explain a p95 afterwards. The
    console stays quiet for these unless --verbose-requests is given, since
    printing them would bury the narration.
    """
    _tracer.emit(
        "http",
        method=method,
        url=url,
        request_body=_clip(request_body),
        request_headers=_headers(headers),
        status=status,
        elapsed_ms=round(elapsed_ms, 1),
        response_body=_clip(response_body),
        response_headers=_headers(response_headers),
        error=error,
    )
    if _tracer.verbose_requests:
        outcome = error or status
        _tracer.say(f"      {method} {url} -> {outcome} in {elapsed_ms:.0f}ms")


def _headers(headers: Any) -> dict[str, str]:
    """Keep the headers that carry evidence, drop the noise.

    Retry-After and the correlation id are part of what the scenarios assert on;
    Content-Length and Server are not, and a full header dump on every one of
    several thousand requests makes the log unusable.
    """
    if not headers:
        return {}
    keep = (
        "retry-after", "x-request-id", "x-correlation-id", "content-type",
        "x-ratelimit-remaining", "cache-control", "traceparent",
    )
    return {k: v for k, v in dict(headers).items() if k.lower() in keep}


def _clip(body: Any) -> Any:
    if body is None:
        return None
    if isinstance(body, (dict, list)):
        text = json.dumps(body, default=str)
        if len(text) <= _MAX_BODY_CHARS:
            return body
        return text[:_MAX_BODY_CHARS] + f"... [{len(text)} chars total]"
    text = str(body)
    return text if len(text) <= _MAX_BODY_CHARS else text[:_MAX_BODY_CHARS] + "..."


def brief(body: Any) -> str:
    """One-line rendering of a body, for console use."""
    if body is None:
        return "-"
    text = json.dumps(body, default=str) if isinstance(body, (dict, list)) else str(body)
    text = " ".join(text.split())
    return text if len(text) <= _MAX_CONSOLE_CHARS else text[:_MAX_CONSOLE_CHARS] + "..."


def summarise_workload(label: str, workload: Any, extra: dict[str, Any] | None = None) -> None:
    """Print and log the aggregate shape of a batch of requests.

    The individual requests are already in the file; this is the line a human
    reads -- how many, what came back, how slow.
    """
    dist = workload.status_distribution()
    fields = {
        "count": workload.count,
        "status_distribution": dist,
        "success_rate": round(workload.success_rate(), 4),
        "p95_ms": round(workload.p95_ms(), 1),
        "max_ms": round(workload.max_ms(), 1),
        **(extra or {}),
    }
    _tracer.say(
        f"    {label}: n={fields['count']} statuses={dist} "
        f"success={fields['success_rate']:.1%} p95={fields['p95_ms']:.0f}ms"
    )
    _tracer.emit("workload", label=label, **fields)


def response_line(label: str, resp: Any, expected: Any = None) -> None:
    """Print and log a single notable response.

    Used where one request carries the meaning of a whole step -- the unwarmed
    read in ASR-A3, the timing-out read in ASR-A1 -- and the aggregate view
    would hide it.
    """
    got = resp.error if resp.status is None else resp.status
    code = resp.error_code() if hasattr(resp, "error_code") else None
    line = f"    {label}: {got}"
    if code:
        line += f" [{code}]"
    if expected is not None:
        line += f" (expected {expected})"
    line += f" in {resp.elapsed_ms:.0f}ms  body={brief(resp.body)}"
    _tracer.say(line)
    _tracer.emit(
        "response", label=label, status=resp.status, error_code=code,
        elapsed_ms=round(resp.elapsed_ms, 1), expected=str(expected) if expected is not None else None,
        body=_clip(resp.body), error=resp.error,
    )
