# Quick Start — IDI Sandbox

## Prerequisites

### 1. Python 3.10+
Download from [python.org](https://www.python.org/downloads/). Make sure "Add Python to PATH" is checked during installation.

### 2. Node.js
Download from [nodejs.org](https://nodejs.org) (LTS recommended).
On Windows you can also use [nvm-windows](https://github.com/coreybutler/nvm-windows) — `start.py` will find it automatically via the Windows registry.

### 3. llama.cpp binary (build from source)

1. Install **Visual Studio Build Tools 2022** (free):
   - Download from [visualstudio.microsoft.com/downloads](https://visualstudio.microsoft.com/downloads/) → *Tools for Visual Studio* → *Build Tools for Visual Studio 2022*
   - In the installer, select the **"Desktop development with C++"** workload (includes MSVC, CMake, and Ninja)
   - Also install [Git for Windows](https://git-scm.com/download/win) if not already present

2. Open a **Developer Command Prompt for VS 2022** (search in Start Menu — a regular terminal won't have cmake in PATH)

3. From the `sandbox/` directory, run:
   ```bash
   cmake -S llama.cpp -B llama.cpp/build -DLLAMA_BUILD_SERVER=ON
   cmake --build llama.cpp/build --config Release
   ```
   Or simply run `make` if you have GNU Make installed.

   The built binary will be at:
   - `sandbox/llama.cpp/build/bin/Release/llama-server.exe`

### 4. Qwen2.5-Coder-3B-Instruct model (GGUF)
- Download `qwen2.5-coder-3b-instruct-q4_k_m.gguf` from
  [Qwen2.5-Coder-3B-Instruct-GGUF on Hugging Face](https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct-GGUF)
- Place it at: `sandbox/llama.cpp/models/qwen2.5-coder-3b-instruct-q4_k_m.gguf`

---

## One-time setup

```bash
# Python backend dependencies
pip install -r sandbox/backend/requirements.txt

# Frontend dependencies (Node.js must be installed first)
cd sandbox/frontend
npm install
cd ../..
```

---

## Run

```bash
# From the project root:
python sandbox/start.py

# Or from inside sandbox/:
python start.py
```

`start.py` runs a preflight check, starts all three servers, and prints their URLs:

```
llama.cpp →  http://localhost:7860   (inference engine)
Backend   →  http://localhost:5000   (FastAPI proxy)
Frontend  →  http://localhost:5173   ← open this in your browser
```

Press `Ctrl+C` to stop all servers.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `uvicorn is not installed` | `pip install -r sandbox/backend/requirements.txt` |
| `npm was not found` | Install Node.js from [nodejs.org](https://nodejs.org) |
| `node_modules is missing` | `cd sandbox/frontend && npm install` |
| `llama-server not found` | Run the cmake build steps above (from a Developer Command Prompt for VS 2022) |
| Model not found | Check the `.gguf` path shown in the error message |
| cmake not found | Run from a **Developer Command Prompt for VS 2022**, not a regular terminal |
| Build errors | Ensure the **"Desktop development with C++"** workload is installed in VS Build Tools |
| Port 7860 in use | `set LLAMA_CPP_SERVER_PORT=9090` before running `start.py` |
| Slow to start | First model load takes 30–60 s — check `sandbox/llama_server.log` |

See [README.md](README.md) for configuration, context loading, and model customization.
