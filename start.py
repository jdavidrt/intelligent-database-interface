"""
IDI — canonical single-command launcher.

Starts all three servers from the canonical layout:
  - llama.cpp inference  (llama-server from winget/PATH + GGUF model under models/)
  - FastAPI backend      (backend/app/main.py, port 5000)
  - Vite frontend        (frontend/, port 5173)

The llama-server binary is resolved from the winget install location or PATH; the
GGUF model lives at the repo root under models/ (gitignored).

Usage (from repo root):
    python start.py

One-time setup (run once before first launch):
    pip install -r backend/requirements.txt
    cd frontend && npm install
"""

import glob
import importlib.util
import os
import shutil
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))             # repo root
BACKEND_DIR = os.path.join(ROOT, "backend", "app")            # cwd for uvicorn main:app
FRONTEND_DIR = os.path.join(ROOT, "frontend")

# Use the repo venv Python if it exists (avoids broken system-level pip installs)
_venv_python = os.path.join(ROOT, ".venv", "Scripts", "python.exe")
PYTHON = _venv_python if os.path.isfile(_venv_python) else sys.executable

# The GGUF model lives at the repo root under models/ (gitignored). The
# llama-server binary is resolved from winget/PATH by find_llama_server().
MODEL_PATH = os.path.join(
    ROOT, "models", "qwen2.5-coder-3b-instruct-q4_k_m.gguf"
)
ADAPTERS_DIR = os.path.join(ROOT, "adapters")
LLAMA_PORT = os.getenv("LLAMA_CPP_SERVER_PORT", "7860")
LLAMA_LOG = os.path.join(ROOT, "llama_server.log")


# ── finders ──────────────────────────────────────────────────────────────────

def find_npm() -> str | None:
    """Return the full path to npm.cmd / npm, or None if not found."""
    candidates = ["npm.cmd", "npm"] if sys.platform == "win32" else ["npm"]

    for name in candidates:
        path = shutil.which(name)
        if path:
            return path

    if sys.platform != "win32":
        return None

    # nvm-windows stores node/npm in NVM_SYMLINK; that dir may not be in the
    # process-inherited PATH, but it IS in the machine registry.
    import winreg
    reg_key = r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"

    def _reg(name: str) -> str:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_key) as k:
                return winreg.QueryValueEx(k, name)[0]
        except Exception:
            return os.environ.get(name, "")

    for name in candidates:
        path = os.path.join(_reg("NVM_SYMLINK"), name)
        if os.path.isfile(path):
            return path

    nvm_home = _reg("NVM_HOME")
    if nvm_home and os.path.isdir(nvm_home):
        for ver in sorted(os.listdir(nvm_home), reverse=True):
            for name in candidates:
                path = os.path.join(nvm_home, ver, name)
                if os.path.isfile(path):
                    return path

    return None


def pick_gpu_device(binary: str) -> str | None:
    """Choose the discrete GPU, not whichever device llama.cpp lists first.

    The winget build is a Vulkan build, and on this machine it enumerates:

        Vulkan0: Intel(R) UHD Graphics 630   <- integrated, and the default
        Vulkan1: NVIDIA GeForce GTX 1650     <- the card we actually want

    llama.cpp offloads to Vulkan0 unless told otherwise, so `-ngl 99` was
    filling the *integrated* GPU: measured 2026-07-21, that is 8.6 tok/s and
    451 MiB of NVIDIA VRAM in use, against 44.6 tok/s and 2969 MiB when pinned
    to Vulkan1 — a 5.2x difference that silently applied to every benchmark run
    and every interactive session.

    Selection is by vendor rather than by free memory: the iGPU reports ~7.4 GB
    "free" because it shares system RAM, so a memory heuristic picks exactly the
    wrong device. Returns None when nothing scores, leaving llama.cpp's default
    alone rather than guessing.

    Override with IDI_LLAMA_DEVICE (e.g. "Vulkan0", or "none" for CPU).
    """
    override = os.getenv("IDI_LLAMA_DEVICE")
    if override:
        return None if override.lower() == "auto" else override

    try:
        listing = subprocess.run(
            [binary, "--list-devices"], capture_output=True, text=True, timeout=60
        ).stdout
    except Exception:
        return None

    discrete = ("nvidia", "geforce", "rtx", "quadro", "tesla", "radeon", "arc")
    integrated = ("uhd graphics", "iris", "hd graphics", "vega", "llvmpipe")

    best: tuple[int, str] | None = None
    for line in listing.splitlines():
        if ":" not in line or not line.strip().startswith(("Vulkan", "CUDA", "SYCL", "ROCm")):
            continue
        name, _, description = line.strip().partition(":")
        lowered = description.lower()
        if any(token in lowered for token in integrated):
            continue
        if any(token in lowered for token in discrete):
            score = 2
        else:
            continue
        if best is None or score > best[0]:
            best = (score, name.strip())
    return best[1] if best else None


def find_llama_server() -> str | None:
    """Return the path to the llama-server binary, or None if not found."""
    # WinGet install location
    local_app = os.environ.get("LOCALAPPDATA", "")
    winget_dir = os.path.join(
        local_app, "Microsoft", "WinGet", "Packages",
        "ggml.llamacpp_Microsoft.Winget.Source_8wekyb3d8bbwe",
    )
    winget_bin = os.path.join(winget_dir, "llama-server.exe")
    if os.path.isfile(winget_bin):
        return winget_bin

    # Fall back to global PATH
    return shutil.which("llama-server") or shutil.which("llama-server.exe")


# ── preflight ────────────────────────────────────────────────────────────────

def preflight() -> bool:
    ok = True

    venv_uvicorn = os.path.join(ROOT, ".venv", "Scripts", "uvicorn.exe")
    uvicorn_ok = os.path.isfile(venv_uvicorn) or importlib.util.find_spec("uvicorn")
    if not uvicorn_ok:
        print("  [ERROR] uvicorn is not installed.")
        print("          Fix: pip install -r backend/requirements.txt\n")
        ok = False

    npm = find_npm()
    if npm is None:
        print("  [ERROR] npm (Node.js) was not found.")
        print("          Fix: install Node.js from https://nodejs.org\n")
        ok = False
    elif not os.path.isdir(os.path.join(FRONTEND_DIR, "node_modules")):
        print("  [ERROR] frontend/node_modules is missing.")
        print(f"          Fix: cd frontend && {npm} install\n")
        ok = False

    llama = find_llama_server()
    if llama is None:
        print("  [ERROR] llama-server binary not found.")
        print("          Fix: install via: winget install ggml.llamacpp")
        print("               (or build llama.cpp and put llama-server on PATH)\n")
        ok = False

    if not os.path.isfile(MODEL_PATH):
        print(f"  [ERROR] Model not found at:\n          {MODEL_PATH}")
        print("          Download the GGUF model and place it there.\n")
        ok = False

    return ok


# ── llama server ─────────────────────────────────────────────────────────────

def llama_already_running() -> bool:
    # 127.0.0.1, not "localhost": localhost resolves to ::1 first on this
    # machine and the IPv6 attempt hangs a full 2s before falling back to IPv4,
    # which would eat the whole timeout on every poll.
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{LLAMA_PORT}/health", timeout=5
        ) as r:
            return r.status == 200
    except Exception:
        return False


def lora_args() -> list[str]:
    """One --lora flag per trained adapter in adapters/*.gguf.

    --lora-init-without-apply loads them at scale 0; the backend activates the
    right one per agent via POST /lora-adapters (llm_service.load_gguf_adapter).
    """
    args: list[str] = []
    for path in sorted(glob.glob(os.path.join(ADAPTERS_DIR, "*.gguf"))):
        args += ["--lora", path]
        print(f"  LoRA adapter: {os.path.basename(path)}")
    if args:
        args += ["--lora-init-without-apply"]
    return args


def start_llama_server(binary: str) -> subprocess.Popen:
    if llama_already_running():
        print(f"  llama.cpp server already running on port {LLAMA_PORT}.")
        return None  # type: ignore

    print(f"  Starting llama.cpp server (log -> {LLAMA_LOG}) ...", flush=True)

    device = pick_gpu_device(binary)
    device_args = ["--device", device] if device else []
    print(f"  GPU device: {device or 'llama.cpp default (no discrete GPU detected)'}")

    log_f = open(LLAMA_LOG, "w")
    proc = subprocess.Popen(
        [binary, "--model", MODEL_PATH, "--port", LLAMA_PORT, "-ngl", "99"]
        + device_args
        + lora_args(),
        stdout=log_f,
        stderr=log_f,
    )

    for i in range(60):
        time.sleep(1)
        if llama_already_running():
            print(f"  llama.cpp server ready.  ({i + 1}s)")
            return proc
        print(f"\r  Waiting for llama.cpp server... {i + 1}s", end="", flush=True)

    print()
    log_f.close()
    proc.terminate()
    raise RuntimeError(
        f"llama.cpp server did not become healthy after 60 s.\n"
        f"Check {LLAMA_LOG} for details."
    )


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print("\n  IDI — checking dependencies...\n")

    if not preflight():
        print("  Aborted. Fix the issues above and try again.\n")
        sys.exit(1)

    npm_exe = find_npm()
    llama_bin = find_llama_server()
    assert npm_exe and llama_bin

    # Build env with node dir in PATH for child processes (nvm-windows fix)
    child_env = os.environ.copy()
    if os.path.isabs(npm_exe):
        node_dir = os.path.dirname(npm_exe)
        if node_dir not in child_env.get("PATH", ""):
            child_env["PATH"] = node_dir + os.pathsep + child_env.get("PATH", "")

    # 1. llama.cpp inference server (blocks until healthy)
    llama_proc = start_llama_server(llama_bin)

    print("\n  Starting backend and frontend...\n")

    # 2. FastAPI backend (canonical: backend/app/main.py)
    # Run from repo root so `backend.app.*` absolute imports resolve;
    # watch only backend/app to keep the reloader off frontend/node_modules.
    backend = subprocess.Popen(
        [
            PYTHON, "-m", "uvicorn", "backend.app.main:app",
            "--reload", "--reload-dir", BACKEND_DIR,
            "--port", "5000",
        ],
        cwd=ROOT,
        env=child_env,
    )

    # 3. Vite frontend (canonical: frontend/)
    frontend = subprocess.Popen(
        [npm_exe, "run", "dev"],
        cwd=FRONTEND_DIR,
        env=child_env,
    )

    print(f"  llama.cpp ->  http://localhost:{LLAMA_PORT}")
    print("  Backend   ->  http://localhost:5000")
    print("  Frontend  ->  http://localhost:5173")
    print("\n  Press Ctrl+C to stop all servers.\n")

    procs = [p for p in (llama_proc, backend, frontend) if p is not None]
    names = ["llama.cpp", "backend", "frontend"]

    try:
        while True:
            for proc, name in zip(procs, names):
                ret = proc.poll()
                if ret is not None:
                    print(f"\n  {name} exited unexpectedly (code {ret}). Stopping all...")
                    for p in procs:
                        p.terminate()
                    sys.exit(ret)
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n  Shutting down...\n")
        for p in procs:
            p.terminate()
        for p in procs:
            p.wait()
        print("  Done.\n")


if __name__ == "__main__":
    main()
