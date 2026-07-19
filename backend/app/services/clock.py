"""Clock — the single source of "now" for the whole pipeline.

Anything in IDI that needs the current date/time must call this module, never
`datetime.now()` / `date.today()` directly. Two reasons:

1. Prompt grounding: the local model does not know what "now" is (its training
   era is stale), so every execution injects `date_context()` into the
   generation prompts. Relative windows ("last 8 months") then resolve against
   the real current date instead of a guessed literal like YEAR(col) = 2024.

2. Reproducibility: setting IDI_FREEZE_NOW (env var or .env) to an ISO
   timestamp pins the clock — prompts AND executed SQL (the FileConnector's
   CURDATE()/NOW() functions route through here) all see the same frozen
   moment, so gate_d1 / evaluate.py runs with hand-derived expected answers
   produce identical results on any day. Example:

       IDI_FREEZE_NOW=2026-07-17T12:00:00

An unparseable override falls back to the real clock with a warning rather
than crashing the pipeline (fail-safe, same discipline as adapter loading).
"""

from __future__ import annotations

from datetime import date, datetime

from backend.app.config import settings

_warned_bad_freeze = False


def now() -> datetime:
    """Current datetime — frozen when IDI_FREEZE_NOW is set."""
    global _warned_bad_freeze
    frozen = settings.freeze_now
    if frozen:
        try:
            return datetime.fromisoformat(frozen)
        except ValueError:
            if not _warned_bad_freeze:
                print(
                    f"[clock] IDI_FREEZE_NOW={frozen!r} is not ISO format "
                    "(e.g. 2026-07-17T12:00:00) — using the real clock."
                )
                _warned_bad_freeze = True
    return datetime.now()


def today() -> date:
    """Current date — frozen when IDI_FREEZE_NOW is set."""
    return now().date()


def now_str() -> str:
    """MySQL-style 'YYYY-MM-DD HH:MM:SS' — what the engine's NOW() returns."""
    return now().strftime("%Y-%m-%d %H:%M:%S")


def today_str() -> str:
    """'YYYY-MM-DD' — what the engine's CURDATE() returns."""
    return today().isoformat()


def date_context() -> str:
    """The grounding line injected into agent prompts on every execution."""
    n = now()
    return f"Current date: {n.strftime('%Y-%m-%d')} ({n.strftime('%A')})"
