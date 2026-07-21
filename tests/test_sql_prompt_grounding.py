"""Pins the three prompt fixes derived from the 2026-07-21 scored run.

Each test names the failure that motivated it. All three are about what the
model is *told*, which is why they assert on the rendered prompt rather than on
generated SQL — the prompt is deterministic and the SQL is not.
"""

from __future__ import annotations

from backend.app.agents.sql_generator import _build_schema_summary, _render_coded_values

# -- fix 2: plan-scoped schema detail -----------------------------------------


def test_unfocused_summary_lists_every_table_in_detail(soundwave_profile) -> None:
    summary = _build_schema_summary(soundwave_profile)
    assert "  subscriptions:" in summary
    assert "  subscription_plans:" in summary


def test_focused_summary_details_only_the_planned_tables(soundwave_profile) -> None:
    """SPIDER-007's failure, in one assertion.

    The planner correctly returned `{"tables": ["subscription_plans"]}`; the
    emitter joined `subscriptions` and read `s.has_downloads` off it — a column
    it could only have found in the full dump printed above the plan.
    """
    summary = _build_schema_summary(soundwave_profile, focus={"subscription_plans"})
    assert "  subscription_plans:" in summary
    assert "  subscriptions:" not in summary


def test_focused_summary_still_lists_every_table_name(soundwave_profile) -> None:
    """The complete list is the hallucinated-table guard and stays complete.

    Narrowing the detail must not narrow the enumeration, or the model loses
    its only means of knowing which names are real.
    """
    summary = _build_schema_summary(soundwave_profile, focus={"artists"})
    listed = summary.split("Tables (complete list", 1)[1].split("\n", 1)[0]
    for table in soundwave_profile.tables:
        assert table.name in listed


def test_focus_keeps_unqualified_glossary_entries(soundwave_profile) -> None:
    """`is_exp`, `trk_dur_ms` name no table and are the hints most needed.

    SPIDER-008 invented `WHERE explicit = 'True'` for a column actually called
    `is_exp`; dropping bare glossary keys under focus would make that worse.
    """
    summary = _build_schema_summary(soundwave_profile, focus={"tracks"})
    assert "is_exp" in summary
    assert "trk_dur_ms" in summary


def test_focus_drops_glossary_entries_for_other_tables(soundwave_profile) -> None:
    summary = _build_schema_summary(soundwave_profile, focus={"tracks"})
    assert "subscription_plans.has_hifi" not in summary


# -- fix 4: coded values as instructions --------------------------------------


def test_integer_codes_are_rendered_as_a_filter_instruction() -> None:
    """BIRD-008: the old rendering stated the map in the direction opposite to
    the one a filter needs, and the model read it forwards."""
    rendered = _render_coded_values("users.status", {"0": "inactive", "1": "active", "2": "banned"})
    assert "'banned' is users.status = 2" in rendered
    assert "INTEGER" in rendered
    assert "never on the label" in rendered


def test_degenerate_maps_become_an_allowed_value_set() -> None:
    """`event_type: play->play` maps nothing; the useful fact is the closed set.

    EXEC-005 counted every row of play_events instead of filtering to
    `event_type = 'play'` — 1230 against 963.
    """
    rendered = _render_coded_values(
        "event_type", {"play": "play", "skip": "skip", "save": "save", "share": "share"}
    )
    assert "accepts exactly these values" in rendered
    assert "'play'" in rendered
    assert "->" not in rendered


def test_coded_values_reach_the_schema_summary(soundwave_profile) -> None:
    summary = _build_schema_summary(soundwave_profile)
    assert "'banned' is users.status = 2" in summary
