# Sandbox Deployment Instructions

This sandbox is designed to test the Qwen2.5-Coder-3B-Instruct model using llama.cpp in a local environment.

## Prerequisites

1. **Install Python**
   - Download and install Python 3.10 or higher from the [official Python website](https://www.python.org/downloads/).
   - Ensure Python is added to your system PATH during installation.

2. **Install Required Python Packages**
   - Open a terminal and run the following command to install the required dependencies:

     ```bash
     pip install requests
     ```

3. **Install llama.cpp**

   The easiest way to install llama.cpp on Windows is via `winget`:

   ```powershell
   winget install llama.cpp
   ```

   This installs pre-built binaries (`llama-server`, `llama-cli`, etc.) system-wide. No compilation or build tools required.

   > **Note:** The old Makefile-based build has been removed from llama.cpp. If you need to build from source instead, see the [Alternative: Build from Source](#alternative-build-from-source) section below.

4. **Download the Qwen2.5-Coder-3B-Instruct Model**
   - Visit the [official Qwen2.5-Coder-3B-Instruct model page](https://huggingface.co/Qwen/Qwen-2.5-Coder-3B-Instruct) on Hugging Face.
   - Download the model in GGUF format with Quantization Q4_K_M.
   - Place the downloaded model file (e.g., `qwen2.5-coder-3b-instruct-q4_k_m.gguf`) in the `llama.cpp/models/` directory inside the sandbox folder.

5. **Start the llama.cpp Server**
   - Run the following command to start the llama.cpp server with the downloaded model:

     ```powershell
     llama-server --model llama.cpp/models/qwen2.5-coder-3b-instruct-q4_k_m.gguf --port 8080
     ```

   - The server should now be running and accessible at `http://localhost:8080`.

## Running the Sandbox

1. Navigate to the `sandbox` directory of this project:

   ```bash
   cd /path/to/intelligent-database-interface/sandbox
   ```

2. Run the sandbox application:

   ```bash
   python sandbox_app.py
   ```

3. Interact with the model directly in the terminal. Type your query and press Enter to send it to the model. The model's response will be displayed in the terminal.

   Example interaction:

   ```
   Welcome to the Qwen2.5-Coder-3B-Instruct Sandbox!
   Type your query below (type 'exit' to quit):
   You: What is the capital of France?
   Model Response: The capital of France is Paris.
   ```

4. Type `exit` to quit the sandbox.

## Automated Setup

You can use the provided PowerShell script to automate the installation:

```powershell
.\setup_sandbox.ps1
```

The script will install llama.cpp via `winget`, download the model, and start the server.

## Alternative: Build from Source

If you prefer to build llama.cpp from source instead of using pre-built binaries:

1. **Install Visual Studio 2022** with the "Desktop development with C++" workload (includes CMake, Ninja, and MSVC).
2. **Open "Developer PowerShell for VS 2022"** (not a regular PowerShell terminal).
3. Clone and build:

   ```powershell
   git clone https://github.com/ggml-org/llama.cpp.git
   cd llama.cpp
   cmake -B build
   cmake --build build --config Release
   ```

4. The server binary will be at `build/bin/Release/llama-server.exe`.

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
