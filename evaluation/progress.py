"""Live console progress for a scored run.

A sweep spends ~90s per item and the pipeline emits nothing between stages, so
the console looks hung for a minute at a time. The orchestrator already streams
an `AgentEvent` per stage carrying `agent`, `status` and a human message
(`orchestrator._ev`) — this renders it, and answers the two questions an
operator actually has: *which stage is running* and *how long has it been in
that stage*.

The per-stage clock is why there is a ticker thread. Repainting only when an
event arrives freezes the display for the whole duration of the stage — which
is precisely the stage you want a clock on, since `sql_generator` is where the
time goes. A daemon thread repaints once a second so the number moves.

Stdlib only, plain ASCII, no colour: the same frames have to survive
PowerShell, Git Bash and a redirected log on this machine.

Nothing here influences the run. The ETA is a running mean over finished items,
shown for the operator's benefit; item selection was fixed before the first
request and never consults it.
"""

from __future__ import annotations

import shutil
import sys
import threading
import time
from typing import Any, TextIO

BAR_WIDTH = 12
TICK_SECONDS = 1.0

# Compact stage names for the per-item breakdown. An agent missing from this
# map is printed in full rather than dropped — a new pipeline stage should look
# wrong, not vanish.
STAGE_ABBREVIATIONS = {
    "context_manager": "ctx",
    "query_understanding": "qu",
    "sql_generator": "gen",
    "verification": "ver",
    "visualization": "viz",
    "session_manager": "sess",
    "clarification": "clar",
}


def _clock(seconds: float) -> str:
    seconds = int(max(0, seconds))
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:02d}:{seconds:02d}"


class ProgressReporter:
    """One in-place status line plus a permanent line per finished item."""

    def __init__(
        self,
        total: int,
        stream: TextIO | None = None,
        live: bool | None = None,
        tick_seconds: float = TICK_SECONDS,
    ):
        self.total = total
        self.stream = stream or sys.stdout
        # A redirected log gets no \r frames — they would render as a wall of
        # half-overwritten lines rather than an animation.
        self.live = live if live is not None else bool(getattr(self.stream, "isatty", bool)())
        self.tick_seconds = tick_seconds
        self.started = time.time()
        self.index = 0
        self.item_id = ""
        self.agent = ""
        self.message = "starting"
        self.step_started = time.time()
        self.completed = 0
        self.passed = 0
        self.scored = 0
        self.durations: list[float] = []
        self._painted = 0
        # Guards every write to the stream: the ticker paints from its own
        # thread while the main thread may be emitting a permanent line.
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._ticker: threading.Thread | None = None

    # -- lifecycle -------------------------------------------------------------

    def start_item(self, index: int, item_id: str) -> None:
        with self._lock:
            self.index = index
            self.item_id = item_id
            self._set_step("", "sending question")
            self._paint()
        self._start_ticker()

    def on_event(self, event: dict[str, Any]) -> None:
        agent = event.get("agent") or ""
        status = event.get("status") or ""
        message = (event.get("message") or "").strip()
        if status == "done" and not message:
            return
        with self._lock:
            self._set_step(agent, message or status)
            self._paint()

    def finish_item(self, record: dict[str, Any]) -> None:
        with self._lock:
            self.completed += 1
            self._set_step("", "scoring")
            if record.get("wall_ms"):
                self.durations.append(record["wall_ms"] / 1000)
            if record.get("score") in ("pass", "fail"):
                self.scored += 1
                self.passed += record["score"] == "pass"

            mark = {"pass": "PASS", "fail": "FAIL", "void": "VOID"}.get(record.get("score"), "????")
            seconds = (record.get("wall_ms") or 0) / 1000
            line = (
                f"[{self.index:>3}/{self.total}] {record.get('id', ''):<11} {mark:<4} "
                f"{record.get('outcome', ''):<14} {seconds:>6.1f}s  "
                f"{self._stages(record):<34} {(record.get('reason') or '')[:60]}"
            )
            self._write_permanent(line)

    def note(self, text: str) -> None:
        """A one-off message that must survive the animation."""
        with self._lock:
            self._write_permanent(text)

    def close(self) -> None:
        self._stop.set()
        if self._ticker is not None:
            self._ticker.join(timeout=2 * self.tick_seconds)
            self._ticker = None
        with self._lock:
            self._clear()

    # -- the per-stage clock ---------------------------------------------------

    def _set_step(self, agent: str, message: str) -> None:
        """Restart the stage clock whenever the stage actually changes.

        Keyed on (agent, message) rather than agent alone: one agent can report
        several sub-steps, and holding the clock across them would attribute the
        earlier one's time to the later.
        """
        if (agent, message) != (self.agent, self.message):
            self.agent, self.message = agent, message
            self.step_started = time.time()

    def _stages(self, record: dict[str, Any]) -> str:
        """Per-stage seconds for a finished item, e.g. `qu 4.4 gen 18.8 ver 0.0`."""
        latencies = record.get("stage_latencies_ms") or {}
        if not latencies:
            return ""
        return " ".join(
            f"{STAGE_ABBREVIATIONS.get(agent, agent)} {ms / 1000:.1f}"
            for agent, ms in latencies.items()
        )

    def _start_ticker(self) -> None:
        if not self.live or self._ticker is not None:
            return
        self._ticker = threading.Thread(target=self._tick, daemon=True, name="idi-progress")
        self._ticker.start()

    def _tick(self) -> None:
        while not self._stop.wait(self.tick_seconds):
            with self._lock:
                self._paint()

    # -- rendering -------------------------------------------------------------

    def _eta(self) -> str:
        if not self.durations:
            return "eta --:--"
        mean = sum(self.durations) / len(self.durations)
        remaining = max(0, self.total - self.completed)
        return f"eta {_clock(mean * remaining)}"

    def _paint(self) -> None:
        if not self.live:
            return
        # Progress is finished items, not the index in flight: otherwise the
        # bar sits still through the ~90s an item takes and jumps only when the
        # next one starts.
        share = self.completed / self.total if self.total else 0
        filled = int(share * BAR_WIDTH)
        bar = "#" * filled + "-" * (BAR_WIDTH - filled)
        accuracy = f"{self.passed}/{self.scored} ok" if self.scored else "-"
        step = f"{self.agent} {_clock(time.time() - self.step_started)}".strip()

        # `query_understanding` is 19 chars and the clock 5, so the field must
        # be wider than 25 or the longest stage name butts against the message.
        head = (
            f"[{self.index:>3}/{self.total}] {share:>4.0%} [{bar}] {self.item_id:<11} "
            f"{step:<26} "
        )
        tail = f"  {_clock(time.time() - self.started)} total - {self._eta()} - {accuracy}"

        width = shutil.get_terminal_size((120, 24)).columns - 1
        # The free-text message is the first thing sacrificed when the terminal
        # is narrow: the stage name and its clock are what was asked for.
        room = max(0, width - len(head) - len(tail))
        line = (head + self.message[:room].ljust(room) + tail)[:width]

        self.stream.write("\r" + line + " " * max(0, self._painted - len(line)))
        self.stream.flush()
        self._painted = len(line)

    def _clear(self) -> None:
        if self.live and self._painted:
            self.stream.write("\r" + " " * self._painted + "\r")
            self.stream.flush()
            self._painted = 0

    def _write_permanent(self, line: str) -> None:
        self._clear()
        self.stream.write(line.rstrip() + "\n")
        self.stream.flush()
        self._paint()
