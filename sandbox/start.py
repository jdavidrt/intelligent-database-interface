"""
IDI Sandbox — single-command launcher.

Starts all three servers: llama.cpp inference, FastAPI backend, and Vite frontend.

Usage (from project root):
    python sandbox/start.py

Usage (from inside sandbox/):
    python start.py

One-time setup (run once before first launch):
    pip install -r sandbox/backend/requirements.txt
    cd sandbox/frontend && npm install
"""

import importlib.util
import shutil
import subprocess
import sys
import os
import time
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT, "backend")
FRONTEND_DIR = os.path.join(ROOT, "frontend")

MODEL_PATH = os.path.join(ROOT, "llama.cpp", "models", "qwen2.5-coder-3b-instruct-q4_k_m.gguf")
LLAMA_PORT = os.getenv("LLAMA_CPP_SERVER_PORT", "7860")
LLAMA_LOG  = os.path.join(ROOT, "llama_server.log")


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


def find_llama_server() -> str | None:
    """Return the path to the llama-server binary, or None if not found."""
    local_candidates = [
        os.path.join(ROOT, "llama.cpp", "build", "bin", "Release", "llama-server.exe"),
        os.path.join(ROOT, "llama.cpp", "build", "bin", "llama-server"),
        os.path.join(ROOT, "llama.cpp", "llama-server.exe"),
    ]
    for path in local_candidates:
        if os.path.isfile(path):
            return path

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

    if not importlib.util.find_spec("uvicorn"):
        print("  [ERROR] uvicorn is not installed.")
        print("          Fix: pip install -r sandbox/backend/requirements.txt\n")
        ok = False

    npm = find_npm()
    if npm is None:
        print("  [ERROR] npm (Node.js) was not found.")
        print("          Fix: install Node.js from https://nodejs.org\n")
        ok = False
    elif not os.path.isdir(os.path.join(FRONTEND_DIR, "node_modules")):
        print("  [ERROR] sandbox/frontend/node_modules is missing.")
        print(f"          Fix: cd sandbox/frontend && {npm} install\n")
        ok = False

    llama = find_llama_server()
    if llama is None:
        print("  [ERROR] llama-server binary not found.")
        print("          Fix: build llama.cpp (see sandbox/README.md)")
        print("               or install via: winget install ggml.llamacpp\n")
        ok = False

    if not os.path.isfile(MODEL_PATH):
        print(f"  [ERROR] Model not found at:\n          {MODEL_PATH}")
        print("          Download the GGUF model and place it there.\n")
        ok = False

    return ok


# ── llama server ─────────────────────────────────────────────────────────────

def llama_already_running() -> bool:
    try:
        with urllib.request.urlopen(
            f"http://localhost:{LLAMA_PORT}/health", timeout=2
        ) as r:
            return r.status == 200
    except Exception:
        return False


def start_llama_server(binary: str) -> subprocess.Popen:
    if llama_already_running():
        print(f"  llama.cpp server already running on port {LLAMA_PORT}.")
        return None  # type: ignore

    print(f"  Starting llama.cpp server (log → {LLAMA_LOG}) ...", flush=True)
    log_f = open(LLAMA_LOG, "w")
    proc = subprocess.Popen(
        [binary, "--model", MODEL_PATH, "--port", LLAMA_PORT],
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
    print("\n  IDI Sandbox — checking dependencies...\n")

    if not preflight():
        print("  Aborted. Fix the issues above and try again.\n")
        sys.exit(1)

    npm_exe    = find_npm()
    llama_bin  = find_llama_server()
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

    # 2. FastAPI backend
    backend = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--reload", "--port", "5000"],
        cwd=BACKEND_DIR,
        env=child_env,
    )

    # 3. Vite frontend
    frontend = subprocess.Popen(
        [npm_exe, "run", "dev"],
        cwd=FRONTEND_DIR,
        env=child_env,
    )

    print("  llama.cpp →  http://localhost:7860")
    print("  Backend   →  http://localhost:5000")
    print("  Frontend  →  http://localhost:5173")
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
