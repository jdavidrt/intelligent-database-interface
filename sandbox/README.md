# Sandbox Deployment Instructions

This sandbox is designed to test the Qwen2.5-Coder-3B-Instruct model using llama.cpp in a local environment.

## Prerequisites

1.  **Install Python**
    -   Download and install Python 3.10 or higher from the [official Python website](https://www.python.org/downloads/).
    -   Ensure Python is added to your system PATH during installation.

2.  **Install Required Python Packages**:
    ```bash
    pip install requests flask flask-cors
    ```

3.  **Install Build Tools (for building llama.cpp from source)**

    You need **Git**, **CMake**, and a **C++ compiler**.

    **Option A: Visual Studio Build Tools (Recommended for Windows)**

    1.  Go to [Visual Studio Downloads](https://visualstudio.microsoft.com/downloads/).
    2.  Under **Tools for Visual Studio**, download **"Build Tools for Visual Studio 2022"** (free, no IDE required).
    3.  Run the installer and select the **"Desktop development with C++"** workload.
        -   This automatically includes: MSVC compiler, CMake, and Ninja.
    4.  Also install [Git for Windows](https://git-scm.com/download/win) if not already present.
    5.  After installing, use the **"Developer Command Prompt for VS 2022"** (search in Start Menu) to run `make` build commands.

    **Option B: MSYS2 / MinGW (alternative, native `make`)**

    1.  Install [MSYS2](https://www.msys2.org/).
    2.  In the MSYS2 UCRT64 terminal, run:
        ```bash
        pacman -S mingw-w64-ucrt-x86_64-gcc mingw-w64-ucrt-x86_64-cmake git make
        ```

4.  **Download & Place the Model**

    -   Visit [Qwen2.5-Coder-3B-Instruct-GGUF](https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct-GGUF) on Hugging Face.
    -   Download `qwen2.5-coder-3b-instruct-q4_k_m.gguf`.
    -   Place the file at `sandbox/llama.cpp/models/qwen2.5-coder-3b-instruct-q4_k_m.gguf`.

## Running the Sandbox

### Step 1 — Build llama.cpp from Source

From the `sandbox/` directory, run:

```bash
# Windows (native):
build.bat

# Linux/macOS (if make is installed):
make
```

This will automatically:
1.  **Clone** `https://github.com/ggml-org/llama.cpp.git` into `sandbox/llama.cpp/` (skipped if already cloned)
2.  **Configure** with CMake (`-DLLAMA_BUILD_SERVER=ON`)
3.  **Build** in Release mode

The built binary will be placed at:
-   **Windows**: `sandbox/llama.cpp/build/bin/Release/llama-server.exe`
-   **Linux/macOS**: `sandbox/llama.cpp/build/bin/llama-server`

You only need to run `make` **once** (or after updating llama.cpp).

### Step 2 — Start the LLM Server

```bash
python sandbox_app.py
```

The server will start on **port `7860`**. Logs are written to `llama_server.log`.

### Step 3 — (Optional) Start the Web Backend

To use the web UI, open a second terminal and run:

```bash
cd sandbox/backend
python app.py
```

The backend API runs on **port `5000`** and proxies requests to the llama server at `7860`.

### Step 4 — Open the Frontend

Open `sandbox/frontend/index.html` in your browser.

---

## Troubleshooting

-   **Port conflicts**: The llama server uses port `7860`. If that's occupied, set: `set LLAMA_CPP_SERVER_PORT=9090` before running `sandbox_app.py`.
-   **Build errors**: Ensure you are running `make` from a **Developer Command Prompt for VS 2022** (not a regular terminal).
-   **Slow startup**: The first model load can take 30–60 seconds. Check `llama_server.log` for progress.
-   **Model not found**: Verify the `.gguf` file is at `sandbox/llama.cpp/models/qwen2.5-coder-3b-instruct-q4_k_m.gguf`.

## Notes

- Ensure that the llama.cpp server is running with the Qwen2.5-Coder-3B-Instruct model and Quantization Q4_K_M (GGUF format) before starting the sandbox.
- Replace the placeholder server URL in the `LLAMA_CPP_SERVER_URL` environment variable if needed.
- The sandbox is designed to interact with the model via the llama.cpp server's HTTP API.

## Sandbox Model Tuning & Customization

This section explains how to tune and customize the AI model running in the sandbox environment.

### Current Model
The sandbox currently uses **Qwen2.5-Coder-3B-Instruct**.
- **Format**: GGUF (Quantized to Q4_K_M)
- **Engine**: [llama.cpp](https://github.com/ggerganov/llama.cpp)

### Tuning Options

#### 1. Generation Parameters (Hyperparameters)
You can adjust how the model generates text by modifying the `requests.post` call in `sandbox_app.py`.

The `llama.cpp` server accepts standard OpenAI-compatible parameters:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `temperature` | `0.8` | Controls randomness. Lower (e.g., `0.2`) makes it more deterministic/focused. Higher (e.g., `1.0`) makes it more creative but potentially incoherent. |
| `top_p` | `0.95` | "Nucleus sampling". Restricts tokens to the top probability mass. Lower values (e.g., `0.5`) reduce diversity. |
| `max_tokens` | `inf` | The maximum number of tokens to generate. |
| `presence_penalty` | `0.0` | Penalizes new tokens based on whether they appear in the text so far. |
| `frequency_penalty` | `0.0` | Penalizes new tokens based on their existing frequency in the text so far. |

**How to Code It:**
Open `sandbox_app.py` and update the payload:

```python
            # Within the main loop in sandbox_app.py
            response = requests.post(
                llama_cpp_server_url,
                json={
                    "messages": [
                        {"role": "system", "content": "You are a helpful coding assistant."}, # Optional: Add system prompt
                        {"role": "user", "content": user_input}
                    ],
                    "temperature": 0.7,   # <--- Add these lines
                    "max_tokens": 1024,
                    "top_p": 0.9,
                }
            )
```

#### 2. System Prompts
The current implementation only sends the user input. To "tune" the behavior (e.g., make it more concise, or act like a specific persona), you should add a **System Message**.

**Example:**
```python
"messages": [
    {"role": "system", "content": "You are an expert Python developer. Answer concisely and provide code snippets."},
    {"role": "user", "content": user_input}
]
```

#### 3. Server-Side Tuning (Performance & Context)
The `llama-server` itself has parameters controlling performance and resource usage. These are set in `setup_sandbox.ps1` or `sandbox_app.py` where `llama-server` is started.

**Common Flags:**
- `-c` or `--ctx-size`: Context size (default is usually 512 or 4096 depending on version). Increase this if you want the model to remember more conversation history.
  - Example: `--ctx-size 8192`
- `-ngl` or `--n-gpu-layers`: Number of layers to offload to GPU.
  - Example: `--n-gpu-layers 99` (for full GPU offload if supported)

**How to Update:**
Edit `sandbox_app.py` in the `start_llama_cpp_server` function:

```python
    subprocess.Popen(
        ["llama-server", "--model", model_path, "--port", server_port, "--ctx-size", "8192", "--n-gpu-layers", "30"],
        # ...
    )
```

#### 4. Changing the Model
To use a different model (e.g., Llama-3-8B or a larger Qwen model):
1. Download the `.gguf` file (e.g., from Hugging Face).
2. Place it in `sandbox/llama.cpp/models/`.
3. Update the `LLAMA_CPP_MODEL_PATH` environment variable OR edit the default value in `sandbox_app.py`:

```python
model_path = os.getenv("LLAMA_CPP_MODEL_PATH", "llama.cpp/models/YOUR_NEW_MODEL.gguf")
```

### Fine-Tuning
"Fine-tuning" usually refers to training the model on new data.
- **Direct GGUF Fine-tuning**: Not directly supported. You typically fine-tune the base model (PyTorch) using tools like `axolotl` or `unsloth`, and *then* convert/quantize to GGUF.
- **LoRA Adapters**: `llama.cpp` supports loading LoRA adapters with `--lora`. If you have a trained adapter, you can pass it to the server start command.

### Context Loading (RAG-lite)
You can provide the model with additional context (like database schemas, API documentation, or business rules) without retraining.

1.  Navigate to the `sandbox/context/` directory.
2.  Add your text files there (e.g., `schema.sql`, `api_docs.txt`, `rules.md`).
3.  The sandbox application will automatically read **all** files in this directory and append their content to the System Prompt for every query.

**Example:**
If you place a `schema.sql` file in `sandbox/context/`, the model will be able to answer questions like "Write a SQL query to get all users" using your specific schema.
