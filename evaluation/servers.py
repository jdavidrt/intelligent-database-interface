"""Bring up the servers a scored run needs, and take down only what we started.

`run_benchmarks.py` should be the single command: a benchmark that requires the
operator to remember `python start.py` in another terminal *and* to remember two
environment variables is a benchmark that will eventually be run without them.
Both are silent hazards — a missing `IDI_FREEZE_NOW` voids the run under §1.1,
and a missing `IDI_GREEDY` makes EX a random variable under §1.3 — so this
module sets them itself rather than trusting anyone to.

Reuses `start.py` for everything it already solves (finding the llama-server
binary through winget/PATH, the GGUF path, the LoRA flags, waiting for llama to
report healthy). What is deliberately *not* reused is `start.main()`:

- **No Vite.** The frontend is irrelevant to a corpus sweep, and requiring npm
  and `node_modules` would make a benchmark fail for want of a UI it never opens.
- **No `--reload`.** The reloader is unreliable on this machine, and a restart
  part-way through a five-hour sweep would drop the cached DB profile and skew
  every latency after it. A benchmark backend must be boring.

Ownership rule: a server this process started is stopped when the run ends; a
server that was already running is left alone, including on Ctrl-C. Killing a
backend someone else is using would be a surprising thing for a benchmark to do.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from typing import Any
from urllib.parse import urlparse

import requests

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import start  # noqa: E402  — the canonical launcher; reused, not reimplemented
from evaluation.corpus import FREEZE_NOW  # noqa: E402

BACKEND_LOG = os.path.join(REPO_ROOT, "backend_server.log")

# The two settings that decide whether a run may be reported at all.
# `IDI_GREEDY_SEED` is left at the backend's default (20260721).
PROTOCOL_ENV = {
    "IDI_FREEZE_NOW": FREEZE_NOW,  # §1.1 — a run without it is void
    "IDI_GREEDY": "1",  # §1.3 — non-greedy makes EX a random variable
}


def _port(base_url: str) -> str:
    return str(urlparse(base_url).port or 5000)


def backend_health(base_url: str, timeout: float = 15.0) -> dict[str, Any] | None:
    """GET /health, or None if it does not answer in time.

    The timeout is generous on purpose. `/health` calls `llm_service.is_healthy()`,
    which probes llama.cpp over HTTP — measured at 4.15s when llama is slow or
    unreachable. A 2s probe here never returned once in 120s of polling against a
    backend that was demonstrably up and answering curl, which is how this
    module first failed.
    """
    try:
        response = requests.get(f"{base_url}/health", timeout=timeout)
        response.raise_for_status()
        return response.json()
    except Exception:
        return None


class ManagedServers:
    """Context manager owning only the processes it started."""

    def __init__(self) -> None:
        self.started: list[tuple[str, subprocess.Popen]] = []

    def __enter__(self) -> ManagedServers:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.shutdown()

    def shutdown(self) -> None:
        for name, proc in reversed(self.started):
            if proc.poll() is not None:
                continue
            print(f"  stopping {name} …")
            proc.terminate()
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()
        self.started.clear()

    # -- llama.cpp -------------------------------------------------------------

    def ensure_llama(self) -> None:
        if start.llama_already_running():
            print(f"  llama.cpp already running on port {start.LLAMA_PORT} — leaving it alone.")
            return

        binary = start.find_llama_server()
        if binary is None:
            raise SystemExit(
                "  llama-server binary not found.\n"
                "  Fix: winget install ggml.llamacpp  (or put llama-server on PATH)"
            )
        if not os.path.isfile(start.MODEL_PATH):
            raise SystemExit(
                f"  Model not found at:\n    {start.MODEL_PATH}\n"
                "  Download the GGUF and place it there."
            )

        proc = start.start_llama_server(binary)
        if proc is not None:
            self.started.append(("llama.cpp", proc))

    # -- FastAPI backend -------------------------------------------------------

    def ensure_backend(self, base_url: str, wait_seconds: int = 120) -> dict[str, Any]:
        """Start the backend if nothing is listening, then wait for health.

        Returns the /health payload. A backend that was already running is
        adopted as-is — its environment is then checked by `run.preflight`,
        which is the component that owns the §1.1/§1.3 verdict.
        """
        health = backend_health(base_url)
        if health is not None:
            print(f"  backend already running at {base_url} — leaving it alone.")
            return health

        env = os.environ.copy()
        env.update(PROTOCOL_ENV)
        print(
            f"  starting backend on port {_port(base_url)} "
            f"(log -> {os.path.basename(BACKEND_LOG)}) …"
        )
        print(f"    IDI_FREEZE_NOW={PROTOCOL_ENV['IDI_FREEZE_NOW']}  IDI_GREEDY=1")

        log = open(BACKEND_LOG, "w", encoding="utf-8")
        proc = subprocess.Popen(
            [
                start.PYTHON,
                "-m",
                "uvicorn",
                "backend.app.main:app",
                "--port",
                _port(base_url),
            ],
            cwd=REPO_ROOT,
            env=env,
            stdout=log,
            stderr=log,
        )
        self.started.append(("backend", proc))

        # Deadline-based, not iteration-based: a single health probe can take
        # several seconds while llama.cpp is still warming, so counting loops
        # would not count seconds.
        deadline = time.time() + wait_seconds
        while time.time() < deadline:
            time.sleep(1)
            if proc.poll() is not None:
                # Losing the port race is not a failure. Another backend may
                # have come up between our health probe and our bind — adopt it
                # rather than aborting a run the operator asked for.
                self.started = [entry for entry in self.started if entry[1] is not proc]
                adopted = backend_health(base_url, timeout=3.0)
                if adopted is not None:
                    print(
                        f"\r  another backend claimed port {_port(base_url)} first — "
                        f"adopting it and leaving it alone." + " " * 10
                    )
                    return adopted
                raise SystemExit(
                    f"\n  backend exited during startup (code {proc.returncode}).\n"
                    f"  See {BACKEND_LOG}"
                )
            waited = int(wait_seconds - (deadline - time.time()))
            health = backend_health(base_url, timeout=10.0)
            if health is not None:
                print(f"\r  backend ready. ({waited}s)" + " " * 24)
                return health
            print(f"\r  waiting for the backend… {waited}s", end="", flush=True)

        raise SystemExit(
            f"\n  backend did not become healthy in {wait_seconds}s. See {BACKEND_LOG}"
        )

    # -- both ------------------------------------------------------------------

    def ensure_all(self, base_url: str) -> dict[str, Any]:
        self.ensure_llama()
        return self.ensure_backend(base_url)
