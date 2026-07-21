"""LLM Service — wraps llama.cpp and exposes adapter hot-swap + base fallback.

Two adapter kinds coexist (selected per agent by adapters/registry.json):
- instruction profile: backend/app/prompts/<name>.md, prepended to the system
  message (load_adapter).
- trained GGUF LoRA: adapters/<name>.gguf, served by llama.cpp (started with
  one --lora flag per file, see start.py) and activated per agent by setting
  its scale to 1.0 via POST /lora-adapters (load_gguf_adapter). While a GGUF
  adapter is active the .md profile is NOT prepended — the specialization is
  in the weights, and the adapter was trained on the bare agent SYSTEM_PROMPT.
"""

from __future__ import annotations

import glob
import os
import time
from typing import Any

import requests

from backend.app.config import settings


class LLMService:
    """Single point of contact for the llama.cpp inference server."""

    def __init__(self) -> None:
        self._base_url: str = settings.llama_cpp_server_url
        self._active_adapter: str | None = None
        self._instruction_profile: str = ""
        # GGUF-name -> server-side adapter id, filled by the first successful
        # GET /lora-adapters (None = never fetched; failures are not cached).
        self._lora_ids: dict[str, int] | None = None

    # -- health ------------------------------------------------------------------

    def is_healthy(self) -> bool:
        try:
            url = self._base_url.replace("/v1/chat/completions", "/health")
            r = requests.get(url, timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    # -- inference ---------------------------------------------------------------

    def _request(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        timeout: int,
        extra: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], int]:
        """POST to llama.cpp; return the raw JSON body and elapsed ms."""
        if self._instruction_profile:
            if messages and messages[0]["role"] == "system":
                messages = [
                    {
                        "role": "system",
                        "content": self._instruction_profile + "\n\n" + messages[0]["content"],
                    }
                ] + messages[1:]
            else:
                messages = [{"role": "system", "content": self._instruction_profile}] + messages

        payload: dict[str, Any] = {"messages": messages, "temperature": temperature}
        if settings.greedy:
            # Applied here rather than at each call site so no agent can opt out
            # of a scored run's decoding contract by passing its own temperature
            # (EVALUATION_PROTOCOL.md §1.3). Set after `temperature` and before
            # `extra` so the caller's value is the one being overridden; `extra`
            # carries grammars, never sampling parameters.
            payload["temperature"] = 0.0
            payload["top_p"] = 1.0
            payload["seed"] = settings.greedy_seed
        if extra:
            # Constrained decoding et al. — e.g. {"response_format": {"type":
            # "json_object", "schema": {...}}} makes llama.cpp compile the JSON
            # Schema (enums included) to a GBNF grammar: the sampler is then
            # physically unable to emit a value outside the schema's vocabulary.
            payload.update(extra)
        t0 = time.time()
        try:
            resp = requests.post(self._base_url, json=payload, timeout=timeout)
            resp.raise_for_status()
        except requests.exceptions.Timeout:
            raise TimeoutError(f"llama.cpp timed out after {timeout}s.")
        except requests.exceptions.ConnectionError:
            raise ConnectionError(f"Cannot reach llama.cpp at {self._base_url}. Is it running?")
        elapsed = round((time.time() - t0) * 1000)
        return resp.json(), elapsed

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        timeout: int = 90,
        extra: dict[str, Any] | None = None,
    ) -> str:
        """Send a chat payload to llama.cpp and return the content string."""
        data, elapsed = self._request(messages, temperature, timeout, extra)
        content: str = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        print(f"[LLMService] {elapsed}ms — {len(content)} chars returned")
        return content

    def chat_with_meta(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        timeout: int = 90,
        extra: dict[str, Any] | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Like chat(), but also returns timing/token metadata for benchmarking.

        Takes `extra` for the same reason chat() does: structured SQL emission
        is both a grammar-constrained call *and* the call whose tokens/sec the
        benchmark reads, so it needs the two capabilities in one place.
        """
        data, elapsed = self._request(messages, temperature, timeout, extra)
        content: str = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        usage = data.get("usage", {})
        completion_tokens = usage.get("completion_tokens", 0)
        meta = {
            "elapsed_ms": elapsed,
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": completion_tokens,
            "tokens_per_sec": (
                round(completion_tokens / (elapsed / 1000), 2)
                if elapsed and completion_tokens
                else None
            ),
        }
        print(f"[LLMService] {elapsed}ms — {len(content)} chars returned")
        return content, meta

    # -- adapter hot-swap: instruction profiles + trained GGUF LoRAs --------------

    def _server_root(self) -> str:
        return self._base_url.replace("/v1/chat/completions", "")

    def _gguf_server_adapters(self) -> dict[str, int]:
        """GGUF basename stem -> server-side adapter id (GET /lora-adapters).

        Cached after the first successful query; an unreachable server returns
        {} without caching, so a late-starting llama.cpp still gets picked up.
        """
        if self._lora_ids is not None:
            return self._lora_ids
        # No trained adapters on disk -> nothing to query or scale. This keeps
        # profile-only deployments (and the offline test suite) fully off the
        # network: the glob is microseconds, a connect attempt is not.
        if not glob.glob(os.path.join(settings.repo_root, "adapters", "*.gguf")):
            return {}
        try:
            r = requests.get(f"{self._server_root()}/lora-adapters", timeout=3)
            r.raise_for_status()
            mapping: dict[str, int] = {}
            for entry in r.json():
                stem = os.path.splitext(os.path.basename(entry.get("path", "")))[0]
                mapping[stem] = entry["id"]
            self._lora_ids = mapping
            return mapping
        except Exception:
            return {}

    def _set_lora_scales(self, active: str | None) -> bool:
        """Scale the active adapter to 1.0 and every other served adapter to 0.0."""
        mapping = self._gguf_server_adapters()
        if not mapping:
            return False
        if active is not None and active not in mapping:
            return False
        payload = [
            {"id": aid, "scale": 1.0 if name == active else 0.0} for name, aid in mapping.items()
        ]
        try:
            r = requests.post(f"{self._server_root()}/lora-adapters", json=payload, timeout=5)
            r.raise_for_status()
            return True
        except Exception as e:
            print(f"[LLMService] POST /lora-adapters failed: {e}")
            return False

    def load_gguf_adapter(self, adapter_name: str) -> bool:
        """Activate the trained LoRA at adapters/<adapter_name>.gguf.

        Returns False (caller falls back to the instruction profile) when the
        file is absent or the llama.cpp server isn't serving that adapter.
        """
        gguf = os.path.join(settings.repo_root, "adapters", f"{adapter_name}.gguf")
        if not os.path.isfile(gguf):
            return False
        if not self._set_lora_scales(adapter_name):
            print(
                f"[LLMService] {adapter_name}.gguf exists but the server is not serving "
                "it (restart via start.py to pass --lora); using instruction profile."
            )
            return False
        # Trained on the bare agent SYSTEM_PROMPT — never double-prompt with the .md.
        self._instruction_profile = ""
        self._active_adapter = adapter_name
        return True

    def load_adapter(self, adapter_name: str) -> None:
        """Activate the instruction profile at backend/app/prompts/<adapter_name>.md.

        Its content is prepended to the system message of subsequent calls. Any
        GGUF LoRA scale left active by a previous agent is zeroed so profile-only
        agents always run against the base model.
        """
        path = os.path.join(os.path.dirname(__file__), "..", "prompts", f"{adapter_name}.md")
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                self._instruction_profile = f.read()
            self._active_adapter = adapter_name
        else:
            # Fail-safe: missing profile never blocks the pipeline.
            self._instruction_profile = ""
            self._active_adapter = None
            print(f"[LLMService] no profile for '{adapter_name}' - base instructions.")
        self._set_lora_scales(None)

    def unload_adapter(self) -> None:
        self._instruction_profile = ""
        self._active_adapter = None
        self._set_lora_scales(None)

    def active_adapter(self) -> str | None:
        return self._active_adapter


# Module-level singleton — import this everywhere.
llm_service = LLMService()
