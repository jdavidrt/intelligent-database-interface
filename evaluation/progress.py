"""Live console progress for a scored run.

A sweep spends ~55s per item and emits nothing until the item finishes, so the
console looks hung for a minute at a time. The pipeline already streams an
`AgentEvent` per stage carrying `agent`, `status` and a human message
(`orchestrator._ev`), which is exactly the "what is it doing right now" signal —
this renders it.

Stdlib only, plain ASCII, no colour: the same frames have to survive PowerShell,
Git Bash and a redirected log on this machine.

Nothing here influences the run. The ETA is a running mean over finished items,
shown for the operator's benefit; item selection was fixed before the first
request and never consults it.
"""

from __future__ import annotations

import shutil
import sys
import time
from typing import Any, TextIO

BAR_WIDTH = 12


def _clock(seconds: float) -> str:
    seconds = int(max(0, seconds))
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:02d}:{seconds:02d}"


class ProgressReporter:
    """One in-place status line plus a permanent line per finished item."""

    def __init__(self, total: int, stream: TextIO | None = None, live: bool | None = None):
        self.total = total
        self.stream = stream or sys.stdout
        # A redirected log gets no \r frames — they would render as a wall of
        # half-overwritten lines rather than an animation.
        self.live = live if live is not None else bool(getattr(self.stream, "isatty", bool)())
        self.started = time.time()
        self.index = 0
        self.item_id = ""
        self.step = "starting"
        self.completed = 0
        self.passed = 0
        self.scored = 0
        self.durations: list[float] = []
        self._painted = 0

    # -- lifecycle -------------------------------------------------------------

    def start_item(self, index: int, item_id: str) -> None:
        self.index = index
        self.item_id = item_id
        self.step = "sending"
        self._paint()

    def on_event(self, event: dict[str, Any]) -> None:
        agent = event.get("agent") or ""
        status = event.get("status") or ""
        message = (event.get("message") or "").strip()
        if status == "done" and not message:
            return
        self.step = f"{agent} {message}".strip() if message else f"{agent} {status}".strip()
        self._paint()

    def finish_item(self, record: dict[str, Any]) -> None:
        self.completed += 1
        self.step = "scoring"
        if record.get("wall_ms"):
            self.durations.append(record["wall_ms"] / 1000)
        if record.get("score") in ("pass", "fail"):
            self.scored += 1
            self.passed += record["score"] == "pass"

        mark = {"pass": "PASS", "fail": "FAIL", "void": "VOID"}.get(record.get("score"), "????")
        line = (
            f"[{self.index:>3}/{self.total}] {record.get('id', ''):<11} {mark:<4} "
            f"{record.get('outcome', ''):<14} {record.get('wall_ms', 0):>6}ms  "
            f"{(record.get('reason') or '')[:70]}"
        )
        self._write_permanent(line)

    def note(self, text: str) -> None:
        """A one-off message that must survive the animation."""
        self._write_permanent(text)

    def close(self) -> None:
        self._clear()

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
        line = (
            f"[{self.index:>3}/{self.total}] {share:>4.0%} [{bar}] {self.item_id:<11} "
            f"{self.step:<36.36} {_clock(time.time() - self.started)} - "
            f"{self._eta()} - {accuracy}"
        )
        width = shutil.get_terminal_size((120, 24)).columns - 1
        line = line[:width]
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
        self.stream.write(line + "\n")
        self.stream.flush()
        self._paint()
