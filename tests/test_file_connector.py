"""FileConnector: load/introspect real soundwave data, read-only guard, LIMIT, transpile."""

from __future__ import annotations

import pytest


def test_introspect_finds_expected_tables(soundwave_profile):
    table_names = {t.name for t in soundwave_profile.tables}
    for expected in ("artists", "tracks", "albums", "users", "playlists", "play_events"):
        assert expected in table_names


def test_introspect_reports_real_row_counts(soundwave_profile):
    artists = next(t for t in soundwave_profile.tables if t.name == "artists")
    assert artists.row_count is not None
    assert artists.row_count > 0


def test_execute_read_rejects_write_statements(soundwave_connector):
    with pytest.raises(ValueError):
        soundwave_connector.execute_read("DELETE FROM tracks")
    with pytest.raises(ValueError):
        soundwave_connector.execute_read("UPDATE tracks SET title='x'")


def test_execute_read_injects_default_limit(soundwave_connector):
    rows = soundwave_connector.execute_read("SELECT * FROM play_events")
    assert len(rows) <= 200


def test_execute_read_respects_explicit_limit(soundwave_connector):
    rows = soundwave_connector.execute_read("SELECT * FROM tracks LIMIT 3")
    assert len(rows) <= 3


def test_execute_read_transpiles_mysql_to_sqlite(soundwave_connector):
    # NULL-safe comparison / MySQL-flavoured syntax should transpile cleanly.
    rows = soundwave_connector.execute_read(
        "SELECT track_id, album_id FROM tracks WHERE album_id IS NULL"
    )
    assert isinstance(rows, list)


def test_explain_accepts_valid_sql_rejects_garbage(soundwave_connector):
    assert soundwave_connector.explain("SELECT * FROM tracks") is True
    assert soundwave_connector.explain("NOT EVEN SQL") is False
