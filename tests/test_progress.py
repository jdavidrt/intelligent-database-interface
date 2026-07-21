"""Pins the live progress display.

Offline, no backend: the reporter writes to a StringIO with `live=True` forced,
so the carriage-return frames it would send to a terminal are inspectable as
text.

The load-bearing behaviour is the ticker. The pipeline emits no AgentEvent
between stages, and `sql_generator` is a ~60s stage, so a display that repaints
only on events shows a frozen clock during exactly the stage an operator wants
timed. Two tests below exist for that alone.
"""

from __future__ import annotations

import io
import time

from evaluation.progress import ProgressReporter

CR = "\r"


def _reporter(**overrides) -> tuple[ProgressReporter, io.StringIO]:
    buf = io.StringIO()
    options = {"total": 10, "stream": buf, "live": True, "tick_seconds": 0.05}
    options.update(overrides)
    return ProgressReporter(**options), buf


def _frames(buf: io.StringIO) -> list[str]:
    return [frame for frame in buf.getvalue().split(CR) if frame.strip()]


# -- the per-stage clock -------------------------------------------------------


def test_stage_clock_resets_when_the_stage_changes() -> None:
    reporter, _ = _reporter()
    reporter.start_item(1, "SPIDER-001")
    reporter.on_event({"agent": "query_understanding", "status": "started", "message": "Parsing"})
    first = reporter.step_started
    time.sleep(0.02)
    reporter.on_event({"agent": "sql_generator", "status": "started", "message": "Generating"})
    reporter.close()
    assert reporter.step_started > first
    assert reporter.agent == "sql_generator"


def test_stage_clock_survives_a_repeated_identical_event() -> None:
    """Restarting the clock on a duplicate event would understate the stage."""
    reporter, _ = _reporter()
    reporter.start_item(1, "SPIDER-001")
    event = {"agent": "sql_generator", "status": "started", "message": "Generating"}
    reporter.on_event(event)
    first = reporter.step_started
    time.sleep(0.02)
    reporter.on_event(dict(event))
    reporter.close()
    assert reporter.step_started == first


def test_two_substeps_of_one_agent_are_timed_separately() -> None:
    """Keyed on (agent, message): holding the clock across sub-steps would
    charge the first one's time to the second."""
    reporter, _ = _reporter()
    reporter.start_item(1, "SPIDER-001")
    reporter.on_event({"agent": "sql_generator", "status": "started", "message": "Planning"})
    first = reporter.step_started
    time.sleep(0.02)
    reporter.on_event({"agent": "sql_generator", "status": "started", "message": "Emitting"})
    reporter.close()
    assert reporter.step_started > first


# -- the ticker ----------------------------------------------------------------


def test_the_display_repaints_without_any_event() -> None:
    """The reason a thread exists. `sql_generator` streams nothing for ~60s; a
    display that waits for an event shows a frozen clock through all of it."""
    reporter, buf = _reporter()
    reporter.start_item(1, "SPIDER-001")
    reporter.on_event({"agent": "sql_generator", "status": "started", "message": "Generating"})
    painted_before = len(_frames(buf))
    time.sleep(0.3)
    painted_after = len(_frames(buf))
    reporter.close()
    assert painted_after > painted_before + 1


def test_close_stops_the_ticker() -> None:
    reporter, buf = _reporter()
    reporter.start_item(1, "SPIDER-001")
    time.sleep(0.1)
    reporter.close()
    quiet = buf.getvalue()
    time.sleep(0.2)
    assert buf.getvalue() == quiet, "the ticker kept painting after close()"


def test_permanent_lines_are_not_corrupted_by_the_ticker() -> None:
    """The ticker paints from its own thread while the main thread writes
    results; without the lock the two interleave mid-line."""
    reporter, buf = _reporter()
    reporter.start_item(1, "SPIDER-001")
    for index in range(6):
        reporter.finish_item(
            {
                "id": f"SPIDER-{index:03d}",
                "score": "pass",
                "outcome": "answered",
                "wall_ms": 1000,
                "reason": "ok",
            }
        )
        time.sleep(0.03)
    reporter.close()
    results = [line for line in buf.getvalue().replace(CR, "\n").split("\n") if "PASS" in line]
    assert len(results) == 6
    for line in results:
        assert line.count("PASS") == 1, f"interleaved output: {line!r}"


# -- rendering -----------------------------------------------------------------


def test_non_tty_emits_no_carriage_returns() -> None:
    """A redirected log must not fill with half-overwritten frames."""
    reporter, buf = _reporter(live=False)
    reporter.start_item(1, "SPIDER-001")
    reporter.on_event({"agent": "sql_generator", "status": "started", "message": "Generating"})
    reporter.finish_item(
        {"id": "SPIDER-001", "score": "pass", "outcome": "answered", "wall_ms": 1, "reason": "ok"}
    )
    reporter.note("[budget] stopping")
    reporter.close()
    assert CR not in buf.getvalue()
    assert "PASS" in buf.getvalue()


def test_finished_item_reports_its_stage_breakdown() -> None:
    reporter, buf = _reporter(live=False)
    reporter.finish_item(
        {
            "id": "SPIDER-001",
            "score": "pass",
            "outcome": "answered",
            "wall_ms": 23217,
            "reason": "12 row(s) matched",
            "stage_latencies_ms": {"query_understanding": 4399, "sql_generator": 18774},
        }
    )
    reporter.close()
    line = buf.getvalue()
    assert "qu 4.4" in line and "gen 18.8" in line
    assert "23.2s" in line


def test_an_unknown_stage_is_shown_in_full_not_dropped() -> None:
    """A new pipeline stage should look wrong, not disappear."""
    reporter, buf = _reporter(live=False)
    reporter.finish_item(
        {
            "id": "X",
            "score": "pass",
            "outcome": "answered",
            "wall_ms": 1,
            "reason": "",
            "stage_latencies_ms": {"brand_new_agent": 2500},
        }
    )
    reporter.close()
    assert "brand_new_agent 2.5" in buf.getvalue()


def test_progress_tracks_finished_items_not_the_one_in_flight() -> None:
    """The bar must not sit still for the ~90s an item takes and then jump."""
    reporter, buf = _reporter()
    reporter.start_item(1, "A")
    assert "  0%" in _frames(buf)[-1]
    reporter.finish_item({"id": "A", "score": "pass", "outcome": "answered", "wall_ms": 1000})
    assert " 10%" in _frames(buf)[-1]
    reporter.close()
