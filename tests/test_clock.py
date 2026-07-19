"""services/clock.py — the pipeline's single source of "now" + IDI_FREEZE_NOW.

The connector tests exercise the full execution boundary: agent-emitted MySQL
(CURDATE()/DATE_SUB) transpiled and run against SQLite with the clock-backed
registered functions — a frozen clock must govern SQL results, not just prompts.
"""

from __future__ import annotations

from datetime import datetime

import pytest

import backend.app.agents.sql_generator as sg_module
from backend.app.config import settings
from backend.app.models.envelope import Intent
from backend.app.services import clock

FROZEN = "2026-07-17T12:00:00"


@pytest.fixture
def frozen_clock(monkeypatch):
    monkeypatch.setattr(settings, "freeze_now", FROZEN)


def test_now_and_today_follow_freeze(frozen_clock):
    assert clock.now() == datetime(2026, 7, 17, 12, 0, 0)
    assert clock.today_str() == "2026-07-17"
    assert clock.now_str() == "2026-07-17 12:00:00"


def test_date_context_names_the_frozen_date_and_weekday(frozen_clock):
    assert clock.date_context() == "Current date: 2026-07-17 (Friday)"


def test_unfrozen_clock_tracks_real_time(monkeypatch):
    monkeypatch.setattr(settings, "freeze_now", "")
    assert abs((clock.now() - datetime.now()).total_seconds()) < 5


def test_bad_freeze_value_falls_back_to_real_clock(monkeypatch):
    monkeypatch.setattr(settings, "freeze_now", "not-a-timestamp")
    assert abs((clock.now() - datetime.now()).total_seconds()) < 5


# -- Executed SQL shares the clock (FileConnector boundary) ---------------------------


def test_connector_curdate_honors_freeze(soundwave_connector, frozen_clock):
    rows = soundwave_connector.execute_read("SELECT CURDATE() AS d;")
    assert rows[0]["d"] == "2026-07-17"


def test_connector_rolling_window_cutoff_is_deterministic(soundwave_connector, frozen_clock):
    rows = soundwave_connector.execute_read(
        "SELECT DATE_SUB(CURDATE(), INTERVAL 8 MONTH) AS cutoff;"
    )
    assert rows[0]["cutoff"] == "2025-11-17"


def test_connector_year_of_curdate(soundwave_connector, frozen_clock):
    rows = soundwave_connector.execute_read("SELECT YEAR(CURDATE()) AS y;")
    assert rows[0]["y"] == 2026


# -- Prompt grounding: the generator injects the clock on every execution -------------


def test_sql_generator_prompt_carries_current_date(
    frozen_clock, patched_vector_context, monkeypatch, soundwave_connector, soundwave_profile
):
    captured: dict = {}

    def fake_chat_with_meta(messages, temperature=0.3, timeout=90):
        captured["messages"] = messages
        return "### Rationale\nok\n\n### SQL\n```sql\nSELECT 1;\n```", {}

    monkeypatch.setattr(sg_module.llm_service, "chat_with_meta", fake_chat_with_meta)

    intent = Intent(
        raw_query="Most played artists in the last 8 months?",
        time_range="last 8 months",
        plain_restatement="Most played artists in the last 8 months",
    )
    sg_module.SQLGenerator().generate(intent, soundwave_profile)

    user_msg = captured["messages"][1]["content"]
    assert "Current date: 2026-07-17 (Friday)" in user_msg
    assert "last 8 months" in user_msg  # time_range is forwarded, not dropped
