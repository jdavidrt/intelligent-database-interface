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
        # Post-sprint: llm_service will call llama.cpp /lora-adapters here.
        # Until wired, fall through to the prompt profile of the same name.
        pass
    # Note: both branches above fall through to load_adapter(agent_name), so
    # entry["artifact"] is never actually read — the filename is always
    # re-derived as "<agent_name>.md" / "<agent_name>.gguf". Harmless today
    # since every artifact value coincides with that, but a trap if an
    # artifact is ever renamed independently of its agent key.
    llm_service.load_adapter(agent_name)
    return llm_service.active_adapter() or "base"
