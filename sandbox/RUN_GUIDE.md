# How to Run the IDI Sandbox (Web & Terminal)

You have two ways to interact with the sandbox model: the **Terminal Interface** and the **Web Interface**.

---

## 1. Prerequisites
Ensure you have the required Python packages:
```bash
pip install requests flask flask-cors
```

And that you have already **built the llama.cpp server** (one-time setup):
```bash
# From the sandbox/ directory:
build.bat
```

---

## 2. Option A: Web Interface (Recommended)

### Step 1: Start the LLM Server
```bash
cd sandbox
python sandbox_app.py
```
*The server will be running at `http://localhost:7860`.*

### Step 2: Start the Backend API
Open a **new** terminal window and run:
```bash
cd sandbox/backend
python app.py
```
*The API will be running at `http://localhost:5000`.*

### Step 3: Open the Frontend
Open `sandbox/frontend/index.html` in your web browser.

---

## 3. Option B: Terminal Only
If you just want a quick terminal chat without the web UI:
```bash
cd sandbox
python sandbox_app.py
```

---

## Troubleshooting
- **Build errors**: Run `make` from a **Developer Command Prompt for VS 2022** (search in Start Menu), not a regular terminal.
- **Connection Refused**: Ensure the llama server is running — check `llama_server.log`.
- **Port Conflicts**: The llama server uses port `7860`. Override with:
  ```bash
  set LLAMA_CPP_SERVER_PORT=9090   # Windows CMD
  $env:LLAMA_CPP_SERVER_PORT=9090  # PowerShell
  ```
- **Backend also uses port `5000`**: Ensure that port is free too.
