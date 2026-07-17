"""Adapter registry - maps each agent to its active artifact.

kind "prompt" -> backend/app/prompts/<artifact> (instruction profile, active now)
kind "gguf"   -> adapters/<artifact> (LoRA adapter, post-sprint)
Missing registry entry or missing file -> base instructions (fail-safe).
"""

from __future__ import annotations

import json
import os

from backend.app.config import settings
from backend.app.services.llm_service import llm_service

_REGISTRY_PATH = os.path.join(settings.repo_root, "adapters", "registry.json")


def load_registry() -> dict:
    if not os.path.isfile(_REGISTRY_PATH):
        return {}
    with open(_REGISTRY_PATH, encoding="utf-8") as f:
        return json.load(f)


def activate(agent_name: str) -> str:
    """Activate the registered artifact for an agent. Returns a label for AgentEvents."""
    entry = load_registry().get(agent_name)
    if entry is None:
        llm_service.unload_adapter()
        return "base"
    if entry["kind"] == "gguf":
        artifact = entry.get("artifact", f"{agent_name}.gguf")
        stem = os.path.splitext(os.path.basename(artifact))[0]
        if llm_service.load_gguf_adapter(stem):
            return f"lora:{agent_name}"
        # Fail-safe: GGUF missing or not served -> same-named instruction profile.
    # Prompt kind (and every fallback) re-derives the filename as
    # "<agent_name>.md" — entry["artifact"] is only honored for gguf entries.
    llm_service.load_adapter(agent_name)
    return llm_service.active_adapter() or "base"
