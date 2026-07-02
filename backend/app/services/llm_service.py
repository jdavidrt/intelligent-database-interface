"""LLM Service — wraps llama.cpp and exposes adapter hot-swap + base fallback.

v2 semantics: an "adapter" is an instruction profile markdown file at
backend/app/prompts/<name>.md, prepended to the system message. When trained
GGUF adapters land (post-sprint), load_adapter() will call the llama.cpp
/lora-adapters endpoint instead — same signature, same call sites.
"""

from __future__ import annotations
import os
import requests
import time
from typing import Any

from backend.app.config import settings


class LLMService:
    """Single point of contact for the llama.cpp inference server."""

    def __init__(self) -> None:
        self._base_url: str = settings.llama_cpp_server_url
        self._active_adapter: str | None = None
        self._instruction_profile: str = ""

    # -- health ------------------------------------------------------------------

    def is_healthy(self) -> bool:
        try:
            url = self._base_url.replace("/v1/chat/completions", "/health")
            r = requests.get(url, timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    # -- inference ---------------------------------------------------------------

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        timeout: int = 90,
    ) -> str:
        """Send a chat payload to llama.cpp and return the content string."""
        if self._instruction_profile:
            if messages and messages[0]["role"] == "system":
                messages = [{"role": "system",
                             "content": self._instruction_profile + "\n\n" + messages[0]["content"]}] + messages[1:]
            else:
                messages = [{"role": "system", "content": self._instruction_profile}] + messages

        payload: dict[str, Any] = {"messages": messages, "temperature": temperature}
        t0 = time.time()
        try:
            resp = requests.post(self._base_url, json=payload, timeout=timeout)
            resp.raise_for_status()
        except requests.exceptions.Timeout:
            raise TimeoutError(f"llama.cpp timed out after {timeout}s.")
        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                f"Cannot reach llama.cpp at {self._base_url}. Is it running?"
            )
        data = resp.json()
        content: str = (
            data.get("choices", [{}])[0].get("message", {}).get("content", "")
        )
        elapsed = round((time.time() - t0) * 1000)
        print(f"[LLMService] {elapsed}ms — {len(content)} chars returned")
        return content

    # -- adapter hot-swap: instruction profiles now, GGUF later ------------------

    def load_adapter(self, adapter_name: str) -> None:
        """Activate the adapter for the next chat() calls.

        v2 semantics: an adapter is an instruction profile at
        backend/app/prompts/<adapter_name>.md. Its content is prepended
        to the system message of subsequent calls. When a real GGUF file
        exists at adapters/<adapter_name>.gguf (post-sprint), this method
        will call llama.cpp /lora-adapters instead - same signature.
        """
        gguf = os.path.join(settings.repo_root, "adapters", f"{adapter_name}.gguf")
        if os.path.isfile(gguf):
            # Post-sprint branch - wired when trained adapters land.
            print(f"[LLMService] GGUF found for {adapter_name} but hot-swap not wired yet; using instruction profile.")
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

    def unload_adapter(self) -> None:
        self._instruction_profile = ""
        self._active_adapter = None

    def active_adapter(self) -> str | None:
        return self._active_adapter


# Module-level singleton — import this everywhere.
llm_service = LLMService()
