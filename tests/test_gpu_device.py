"""Pins discrete-GPU selection for llama.cpp.

Offline: `pick_gpu_device` is fed captured `llama-server --list-devices` output
rather than invoking the binary.

Why this is worth a test file of its own. The winget llama.cpp build is a Vulkan
build and enumerates the integrated Intel GPU *first*, so `-ngl 99` alone
offloads there. Measured 2026-07-21: 8.6 tok/s and 451 MiB of NVIDIA VRAM on the
iGPU, against 44.6 tok/s and 2969 MiB pinned to the GTX 1650. Nothing failed —
every run simply took five times longer, for months, and the benchmark reported
those numbers as a GPU profile.

The trap worth guarding is the tempting fix: pick the device with the most free
memory. The iGPU reports ~7.4 GB free because it shares system RAM, so that
heuristic confidently selects the slow device. Selection is by vendor, and
`test_free_memory_is_not_the_criterion` is why.
"""

from __future__ import annotations

import pytest

import start

# Captured verbatim from this machine, 2026-07-21.
THIS_MACHINE = """Available devices:
  Vulkan0: Intel(R) UHD Graphics 630 (8241 MiB, 7451 MiB free)
  Vulkan1: NVIDIA GeForce GTX 1650 (4149 MiB, 3555 MiB free)
"""

CUDA_BUILD = """Available devices:
  CUDA0: NVIDIA GeForce RTX 4090 (24564 MiB, 24000 MiB free)
"""

CPU_ONLY = """Available devices:
"""

INTEGRATED_ONLY = """Available devices:
  Vulkan0: Intel(R) UHD Graphics 630 (8241 MiB, 7451 MiB free)
"""


@pytest.fixture
def listing(monkeypatch):
    """Feed `pick_gpu_device` a canned --list-devices output."""

    def _install(text: str):
        class _Result:
            stdout = text

        monkeypatch.setattr(start.subprocess, "run", lambda *a, **k: _Result())
        monkeypatch.delenv("IDI_LLAMA_DEVICE", raising=False)

    return _install


def test_discrete_gpu_wins_over_the_integrated_one(listing) -> None:
    """The whole point: Vulkan1, not the Vulkan0 llama.cpp would default to."""
    listing(THIS_MACHINE)
    assert start.pick_gpu_device("llama-server") == "Vulkan1"


def test_free_memory_is_not_the_criterion(listing) -> None:
    """The iGPU advertises 7451 MiB free against the GTX 1650's 3555, because it
    shares system RAM. A memory heuristic picks the 5x slower device."""
    listing(THIS_MACHINE)
    chosen = start.pick_gpu_device("llama-server")
    assert chosen != "Vulkan0"


def test_a_cuda_build_is_handled_too(listing) -> None:
    listing(CUDA_BUILD)
    assert start.pick_gpu_device("llama-server") == "CUDA0"


@pytest.mark.parametrize("text", [CPU_ONLY, INTEGRATED_ONLY])
def test_no_discrete_gpu_defers_to_llama_cpp(listing, text: str) -> None:
    """None means "don't pass --device" — better than pinning a machine with no
    discrete GPU to a device that may not exist."""
    listing(text)
    assert start.pick_gpu_device("llama-server") is None


def test_env_override_is_honoured(listing, monkeypatch) -> None:
    listing(THIS_MACHINE)
    monkeypatch.setenv("IDI_LLAMA_DEVICE", "Vulkan0")
    assert start.pick_gpu_device("llama-server") == "Vulkan0"


def test_auto_restores_llama_cpp_default(listing, monkeypatch) -> None:
    listing(THIS_MACHINE)
    monkeypatch.setenv("IDI_LLAMA_DEVICE", "auto")
    assert start.pick_gpu_device("llama-server") is None


def test_a_broken_binary_does_not_crash_the_launcher(monkeypatch) -> None:
    """A failed probe must degrade to llama.cpp's default, not abort startup."""
    monkeypatch.delenv("IDI_LLAMA_DEVICE", raising=False)

    def _boom(*_args, **_kwargs):
        raise OSError("binary not executable")

    monkeypatch.setattr(start.subprocess, "run", _boom)
    assert start.pick_gpu_device("llama-server") is None
