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


def test_activate_gguf_kind_without_file_falls_through_to_prompt(
    tmp_registry, tmp_path, monkeypatch
):
    from backend.app.config import settings

    # Point repo_root at an empty dir: no adapters/<name>.gguf exists, so the
    # gguf branch must fall back to the same-named .md profile (fail-safe).
    monkeypatch.setattr(settings, "repo_root", str(tmp_path))
    tmp_registry.write_text(
        json.dumps({"sql_generator": {"kind": "gguf", "artifact": "sql_generator.gguf"}}),
        encoding="utf-8",
    )
    label = adapter_registry.activate("sql_generator")
    assert label == "sql_generator"
    assert llm_service.active_adapter() == "sql_generator"


def test_activate_gguf_kind_with_file_but_no_server_falls_through(
    tmp_registry, tmp_path, monkeypatch
):
    from backend.app.config import settings

    adapters_dir = tmp_path / "adapters"
    adapters_dir.mkdir()
    (adapters_dir / "sql_generator.gguf").write_text("", encoding="utf-8")
    monkeypatch.setattr(settings, "repo_root", str(tmp_path))
    # Unreachable llama.cpp: /lora-adapters can't be queried, so activation
    # must fail-safe back to the instruction profile instead of erroring.
    monkeypatch.setattr(llm_service, "_base_url", "http://127.0.0.1:1/v1/chat/completions")
    monkeypatch.setattr(llm_service, "_lora_ids", None)
    tmp_registry.write_text(
        json.dumps({"sql_generator": {"kind": "gguf", "artifact": "sql_generator.gguf"}}),
        encoding="utf-8",
    )
    label = adapter_registry.activate("sql_generator")
    assert label == "sql_generator"
    assert llm_service.active_adapter() == "sql_generator"


def test_load_gguf_adapter_activates_lora_when_server_serves_it(tmp_path, monkeypatch):
    from backend.app.config import settings

    adapters_dir = tmp_path / "adapters"
    adapters_dir.mkdir()
    (adapters_dir / "sql_generator.gguf").write_text("", encoding="utf-8")
    monkeypatch.setattr(settings, "repo_root", str(tmp_path))
    monkeypatch.setattr(llm_service, "_lora_ids", {"sql_generator": 0})

    posted: list = []
    monkeypatch.setattr(
        llm_service, "_set_lora_scales", lambda active: posted.append(active) or True
    )

    assert llm_service.load_gguf_adapter("sql_generator") is True
    assert posted == ["sql_generator"]
    assert llm_service.active_adapter() == "sql_generator"
    # The .md profile must NOT be prepended while the trained adapter is active.
    assert llm_service._instruction_profile == ""
