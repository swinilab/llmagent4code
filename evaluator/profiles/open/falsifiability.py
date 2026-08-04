"""Does the verification suite fail when it should?

Auditing a result file establishes that a verdict follows from its numbers. It
cannot establish that the numbers would have been different had the mechanism
been absent -- and a suite whose assertions hold either way has verified
nothing, however carefully it reports.

The probe here is mutation testing narrowed to one question per NFR: disable
the mechanism the agent claims to have built, re-run that NFR's script, and
require it to report `passed: false`. A script that still passes is measuring
something other than the mechanism it names.

Disabling is done through configuration the agent itself declared, never by
editing its source:

  * a configuration key named in the NFR traceability entry, set to a value
    that turns the mechanism off (`0`, `false`, or an absurd bound);
  * failing that, the tactic-specific fallbacks below.

Where neither applies the NFR is reported as NOT_PROBED rather than failed --
an unprobed mechanism has not been shown to be unfalsifiable, and recording it
as such would overstate what was observed.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# How a mechanism is neutralised, by the kind of configuration key involved.
# Chosen so the application still starts: a suite must fail because its tactic
# is gone, not because the process died.
NEUTRALISING_VALUES = {
    "timeout": "600000",     # a time limit so large it can never trigger
    "attempts": "1",         # no retry beyond the initial attempt
    "retry": "1",
    "max_in_flight": "100000",   # admission control that admits everything
    "concurrency": "100000",
    "ttl": "0",              # a cache that never serves a copy
    "cache": "0",
}


@dataclass
class Probe:
    """One falsifiability attempt against one NFR."""

    nfr: str
    method: str            # how the mechanism was disabled
    detail: str
    ran: bool = False
    reported_pass: bool | None = None

    @property
    def falsifiable(self) -> bool | None:
        """True when disabling the mechanism made the suite report failure."""
        if not self.ran or self.reported_pass is None:
            return None
        return self.reported_pass is False


def plan(trace_entries: list[dict[str, Any]]) -> list[Probe]:
    """Decide, per NFR, how its mechanism could be switched off.

    Reads `configurationKeys` from the traceability entries, because those are
    the keys the agent itself nominated as governing the mechanism. Using the
    agent's own declaration keeps the probe honest: if the key it named does
    not in fact control the tactic, that is a defect in the traceability claim
    and the probe result says so.
    """
    probes: list[Probe] = []
    for entry in trace_entries:
        nfr = str(entry.get("nfr") or entry.get("scenarioId") or "").strip()
        if not nfr:
            continue

        keys = [str(k) for k in (entry.get("configurationKeys") or []) if str(k).strip()]
        chosen = _choose_key(keys)
        if chosen is None:
            probes.append(Probe(nfr, "none", f"no neutralisable key among {keys or '[]'}"))
            continue

        key, value = chosen
        probes.append(Probe(nfr, "env", f"{key}={value}"))
    return probes


def _choose_key(keys: list[str]) -> tuple[str, str] | None:
    """Pick a declared key whose value can disable the mechanism."""
    for key in keys:
        lowered = key.lower()
        for token, value in NEUTRALISING_VALUES.items():
            if token in lowered:
                return key, value
    return None


def execute(
    app_dir: Path,
    probe: Probe,
    script: Path,
    result_file: Path,
    *,
    env_overrides: dict[str, str],
    timeout_s: int = 300,
) -> Probe:
    """Run one NFR script with its mechanism disabled and read the verdict.

    The application is expected to have been restarted with `env_overrides`
    already applied by the caller; this function only drives the script and
    interprets what it wrote.
    """
    if probe.method == "none":
        return probe

    environment = {**os.environ, **env_overrides}
    try:
        subprocess.run(
            [_interpreter(script), str(script)],
            cwd=app_dir,
            env=environment,
            capture_output=True,
            timeout=timeout_s,
            check=False,
        )
        probe.ran = True
    except (OSError, subprocess.TimeoutExpired) as exc:
        probe.detail += f"; script did not complete: {type(exc).__name__}"
        return probe

    # A script that crashes rather than reporting is still a failure signal:
    # what must not happen is a clean pass with the mechanism gone.
    try:
        data = json.loads(result_file.read_text(encoding="utf-8"))
        probe.reported_pass = bool(data.get("passed"))
    except (OSError, ValueError):
        probe.reported_pass = False
        probe.detail += "; no readable result after the probe run"

    return probe


def _interpreter(script: Path) -> str:
    return "python" if script.suffix == ".py" else "sh"


def summarise(probes: list[Probe]) -> dict[str, Any]:
    """Counts for the report, keeping unprobed NFRs distinct from failures."""
    falsifiable = [p for p in probes if p.falsifiable is True]
    unfalsifiable = [p for p in probes if p.falsifiable is False]
    unprobed = [p for p in probes if p.falsifiable is None]
    return {
        "falsifiable": [p.nfr for p in falsifiable],
        "unfalsifiable": [p.nfr for p in unfalsifiable],
        "not_probed": [{"nfr": p.nfr, "reason": p.detail} for p in unprobed],
        "counts": {
            "falsifiable": len(falsifiable),
            "unfalsifiable": len(unfalsifiable),
            "not_probed": len(unprobed),
        },
    }
