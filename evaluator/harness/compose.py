"""Docker Compose lifecycle and container-level external evidence.

The application is always started the way the submission says it should be --
by the single line in start_command.txt -- rather than by a command the
evaluator invents. If that line does not bring the system up, that is the G0
result, not something to work around.

Container restart counts read from `docker inspect` are the evidence behind
every "process crash and unplanned restart count is 0" measure. An application
that survives overload by crashing and being restarted by Docker looks healthy
over HTTP; it does not look healthy here.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

import httpx


class DeploymentError(RuntimeError):
    """The system could not be built or started -- a G0 NOT_EXECUTABLE."""


@dataclass(frozen=True)
class ContainerState:
    name: str
    running: bool
    restart_count: int
    exit_code: int | None


class Compose:
    def __init__(self, app_dir: Path, project_name: str, timeout: int = 900):
        self.app_dir = Path(app_dir)
        self.project = project_name
        self.timeout = timeout
        if shutil.which("docker") is None:
            raise DeploymentError("docker is not on PATH")

    # ── start command, as declared by the submission ──────────────────────

    def declared_start_command(self) -> str:
        """Read start_command.txt and enforce its 'exactly one line' contract."""
        path = self.app_dir / "start_command.txt"
        if not path.is_file():
            raise DeploymentError("start_command.txt is missing")
        lines = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        if len(lines) != 1:
            raise DeploymentError(
                f"start_command.txt must contain exactly one non-empty line, found {len(lines)}"
            )
        return lines[0]

    def _run(self, args: list[str], timeout: int | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            args,
            cwd=self.app_dir,
            capture_output=True,
            text=True,
            timeout=timeout or self.timeout,
        )

    def _compose(self, *args: str, timeout: int | None = None) -> subprocess.CompletedProcess:
        return self._run(["docker", "compose", "-p", self.project, *args], timeout=timeout)

    # ── lifecycle ─────────────────────────────────────────────────────────

    def up(self) -> subprocess.CompletedProcess:
        """Build and start using the submission's own command.

        The project name is injected so concurrent evaluations of different
        applications cannot collide, but the command itself is otherwise run
        as written.
        """
        cmd = self.declared_start_command()
        parts = cmd.split()
        if parts[:2] == ["docker", "compose"]:
            parts = ["docker", "compose", "-p", self.project, *parts[2:]]
        proc = self._run(parts)
        if proc.returncode != 0:
            raise DeploymentError(f"start command failed: {cmd}\n{proc.stderr[-4000:]}")
        return proc

    def down(self, volumes: bool = True) -> None:
        """Tear down; with volumes=True this also drops the database.

        Used between scenarios so that data accumulated by one scenario --
        especially the orders ASR-A4 leaves behind -- cannot perturb the next.
        """
        args = ["down", "--remove-orphans"]
        if volumes:
            args.append("-v")
        self._compose(*args, timeout=180)

    def recreate(self) -> None:
        """Drop the stack, volumes included, and start it again.

        Between scenarios the image is already built and unchanged, so a
        rebuild is pure cost -- and worse, `--build` consults the registry, so a
        momentary network problem turns a routine reset into a failed bring-up.
        The declared start command is tried first because it is what the
        submission says starts the system; if it fails, the same command without
        `--build` is tried before giving up, since the image from the first
        start is still present and perfectly usable.
        """
        self.down(volumes=True)
        try:
            self.up()
        except DeploymentError as exc:
            proc = self._compose("up", "-d", timeout=self.timeout)
            if proc.returncode != 0:
                raise DeploymentError(
                    f"restart failed both with and without --build: {exc}"
                ) from exc

    # ── container evidence ────────────────────────────────────────────────

    def container_ids(self) -> list[str]:
        proc = self._compose("ps", "-q", timeout=60)
        return [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]

    def inspect(self) -> list[ContainerState]:
        states: list[ContainerState] = []
        for cid in self.container_ids():
            proc = self._run(["docker", "inspect", cid], timeout=60)
            if proc.returncode != 0:
                continue
            data = json.loads(proc.stdout)[0]
            st = data.get("State", {})
            states.append(
                ContainerState(
                    name=data.get("Name", cid).lstrip("/"),
                    running=bool(st.get("Running")),
                    restart_count=int(data.get("RestartCount", 0)),
                    exit_code=st.get("ExitCode"),
                )
            )
        return states

    def total_restarts(self) -> int:
        return sum(c.restart_count for c in self.inspect())

    def app_container(self, hint: str = "app") -> ContainerState | None:
        states = self.inspect()
        for c in states:
            if hint in c.name:
                return c
        return None

    def logs(self, tail: int = 2000) -> str:
        """Container logs -- the diagnostic trail behind a FAIL.

        The prompt requires structured log lines for rejections, timeouts,
        retries, degraded reads and rollbacks, so a failing scenario can be
        explained from here without opening the source.
        """
        proc = self._compose("logs", "--no-color", f"--tail={tail}", timeout=120)
        return proc.stdout + proc.stderr

    # ── readiness ─────────────────────────────────────────────────────────

    def wait_until_ready(self, base_url: str, timeout_s: int = 180) -> float:
        """Poll /health/ready until it answers 200. Returns seconds elapsed."""
        deadline = time.monotonic() + timeout_s
        started = time.monotonic()
        last: str = "no attempt made"
        with httpx.Client(timeout=5.0) as client:
            while time.monotonic() < deadline:
                try:
                    resp = client.get(f"{base_url}/health/ready")
                    if resp.status_code == 200:
                        return time.monotonic() - started
                    last = f"HTTP {resp.status_code}"
                except httpx.RequestError as exc:
                    last = str(exc)
                time.sleep(1.0)
        raise DeploymentError(f"/health/ready never returned 200 within {timeout_s}s; last: {last}")