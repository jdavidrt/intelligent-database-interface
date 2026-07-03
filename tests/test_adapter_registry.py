"""Adapter registry: activation, fail-safe fallback, gguf fall-through."""

from __future__ import annotations

import json

from backend.app.services import adapter_registry
from backend.app.services.llm_service import llm_service


def test_activate_known_agent_loads_real_profile():
    label = adapter_registry.activate("sql_generator")
    assert label == "sql_generator"
    assert llm_service.active_adapter() == "sql_generator"


def test_activate_missing_registry_entry_falls_back_to_base(tmp_registry):
    tmp_registry.write_text(json.dumps({}), encoding="utf-8")
    label = adapter_registry.activate("sql_generator")
    assert label == "base"
    assert llm_service.active_adapter() is None


def test_activate_missing_registry_file_falls_back_to_base(tmp_registry):
    # tmp_registry fixture points _REGISTRY_PATH at a path that doesn't exist yet.
    label = adapter_registry.activate("sql_generator")
    assert label == "base"


def test_activate_missing_profile_file_falls_back_to_base(tmp_registry):
    tmp_registry.write_text(
        json.dumps({"sql_generator": {"kind": "prompt", "artifact": "sql_generator.md"}}),
        encoding="utf-8",
    )
    label = adapter_registry.activate("an_agent_with_no_prompt_file")
    assert label == "base"
    assert llm_service.active_adapter() is None


def test_activate_gguf_kind_falls_through_to_prompt(tmp_registry):
    tmp_registry.write_text(
        json.dumps({"sql_generator": {"kind": "gguf", "artifact": "sql_generator.gguf"}}),
        encoding="utf-8",
    )
    label = adapter_registry.activate("sql_generator")
    # No GGUF hot-swap is wired yet; falls through to the same-named .md profile.
    assert label == "sql_generator"


def test_llm_service_load_adapter_reports_gguf_present_but_not_wired(tmp_path, monkeypatch, capsys):
    from backend.app.config import settings

    adapters_dir = tmp_path / "adapters"
    adapters_dir.mkdir()
    (adapters_dir / "sql_generator.gguf").write_text("", encoding="utf-8")
    monkeypatch.setattr(settings, "repo_root", str(tmp_path))

    llm_service.load_adapter("sql_generator")

    # Prompt lookup is relative to llm_service.py's own location, unaffected
    # by repo_root, so the real profile still loads.
    assert llm_service.active_adapter() == "sql_generator"
    captured = capsys.readouterr()
    assert "not wired yet" in captured.out
