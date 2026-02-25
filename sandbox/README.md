# IDI Sandbox

Local NL2SQL sandbox running **Qwen2.5-Coder-3B-Instruct** via llama.cpp, with a FastAPI backend and a React/TypeScript frontend.

## Architecture

```
start.py
  ├── llama.cpp server   → port 7860  (inference engine)
  ├── backend/main.py    → port 5000  (FastAPI proxy + context loading)
  └── frontend/          → port 5173  (Vite + React + TypeScript)
```

Context files in `sandbox/context/` are auto-loaded into the system prompt on every request.

---

## Prerequisites

### 1. Python packages
```bash
pip install -r sandbox/backend/requirements.txt
```

### 2. Node.js (for frontend)
Install [Node.js](https://nodejs.org) (or via [nvm-windows](https://github.com/coreybutler/nvm-windows) on Windows), then:
```bash
cd sandbox/frontend
npm install
```

### 3. Build llama.cpp (one-time)

**Windows (from `sandbox/` directory):**
```bash
build.bat
```

**Linux/macOS:**
```bash
make
```

This clones `https://github.com/ggml-org/llama.cpp`, configures with CMake (`-DLLAMA_BUILD_SERVER=ON`), and builds in Release mode.

Built binary location:
- **Windows**: `sandbox/llama.cpp/build/bin/Release/llama-server.exe`
- **Linux/macOS**: `sandbox/llama.cpp/build/bin/llama-server`

### 4. Download the model

- Visit [Qwen2.5-Coder-3B-Instruct-GGUF](https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct-GGUF) on Hugging Face.
- Download `qwen2.5-coder-3b-instruct-q4_k_m.gguf`.
- Place it at: `sandbox/llama.cpp/models/qwen2.5-coder-3b-instruct-q4_k_m.gguf`

---

## Running

```bash
# From the project root:
python sandbox/start.py

# Or from inside sandbox/:
python start.py
```

`start.py` runs a preflight check, then starts all three servers. When everything is ready:

```
llama.cpp →  http://localhost:7860
Backend   →  http://localhost:5000
Frontend  →  http://localhost:5173
```

Open `http://localhost:5173` in your browser. Press `Ctrl+C` to stop all servers.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `uvicorn is not installed` | `pip install -r sandbox/backend/requirements.txt` |
| `npm was not found` | Install Node.js from [nodejs.org](https://nodejs.org) |
| `node_modules is missing` | `cd sandbox/frontend && npm install` |
| `llama-server not found` | Run cmake build steps (from a Developer Command Prompt for VS 2022) |
| `Model not found` | Place `.gguf` file at `sandbox/llama.cpp/models/qwen2.5-coder-3b-instruct-q4_k_m.gguf` |
| Build errors on Windows | Run `build.bat` from a **Developer Command Prompt for VS 2022** |
| Port `7860` in use | `set LLAMA_CPP_SERVER_PORT=9090` before running `start.py` |
| Slow startup | First model load takes 30–60 s. Check `llama_server.log` for progress. |

---

## Customization

### Generation parameters
Edit the inference payload in [backend/main.py](backend/main.py) — look for the `requests.post` call to the llama.cpp `/v1/chat/completions` endpoint:

```python
"temperature": 0.7,
"max_tokens": 1024,
"top_p": 0.9,
```

| Parameter | Description |
|---|---|
| `temperature` | Randomness. Lower → more deterministic. Higher → more creative. |
| `top_p` | Nucleus sampling probability mass. |
| `max_tokens` | Maximum tokens to generate. |
| `presence_penalty` | Penalizes tokens already present in the output. |
| `frequency_penalty` | Penalizes high-frequency tokens. |

### llama-server flags
`start.py` launches the binary with `--model` and `--port`. To add flags like GPU offload or larger context, edit the `start_llama_server` function in `start.py`:

```python
[binary, "--model", MODEL_PATH, "--port", LLAMA_PORT, "--n-gpu-layers", "30", "--ctx-size", "8192"]
```

| Flag | Description |
|---|---|
| `--n-gpu-layers N` | Offload N layers to GPU (set high, e.g. 99, for full GPU). |
| `--ctx-size N` | Context window size (default varies; 4096–8192 recommended). |

### Context / RAG
Drop any `.md`, `.sql`, or `.txt` files into `sandbox/context/`. The backend reads all files in that directory and appends them to the system prompt on every request — no restart needed.

### Changing the model
1. Download a different `.gguf` from Hugging Face.
2. Place it in `sandbox/llama.cpp/models/`.
3. Update `MODEL_PATH` at the top of `start.py`.

### Fine-tuning / LoRA
Direct GGUF fine-tuning is not supported. Fine-tune the base model (PyTorch) with tools like `axolotl` or `unsloth`, convert to GGUF, then either swap the model file or pass a LoRA adapter with `--lora` in the server flags.
