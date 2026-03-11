from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import time
import requests
import os
import re
import shutil
import subprocess
import sys
import uuid
import threading

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

app = FastAPI(title="IDI Sandbox Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# llama.cpp server configuration
LLAMA_PORT = os.getenv("LLAMA_CPP_SERVER_PORT", "7860")
LLAMA_CPP_SERVER_URL = os.getenv(
    "LLAMA_CPP_SERVER_URL",
    f"http://localhost:{LLAMA_PORT}/v1/chat/completions",
)

SANDBOX_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
CONTEXT_DIR = os.path.join(SANDBOX_ROOT, "context")
MODEL_PATH = os.path.join(
    SANDBOX_ROOT, "llama.cpp", "models",
    "qwen2.5-coder-3b-instruct-q4_k_m.gguf",
)

# ── context & system prompt ───────────────────────────────────────────────────

def load_context() -> str:
    combined = ""
    if os.path.exists(CONTEXT_DIR):
        for filename in sorted(os.listdir(CONTEXT_DIR)):
            file_path = os.path.join(CONTEXT_DIR, filename)
            if os.path.isfile(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        combined += f"\n\n--- Context from {filename} ---\n"
                        combined += f.read()
                except Exception as e:
                    print(f"Warning: Could not read {filename}: {e}")
    return combined


def build_system_prompt() -> str:
    system_content = (
        "You are IDI (Intelligent Database Interface), a Natural Language to SQL model. "
        "Your goal is to generate accurate SQL queries based on the provided database context. "
        "CRITICAL: Always verify that every table mentioned in your SQL (SELECT, FROM, JOIN, etc.) "
        "exactly matches the table names defined in the provided context (especially within 'README.txt'). "
        "If a user asks for a table that is not found in the context, do not invent it; "
        "instead, politely inform them that the table is not defined in the current schema.\n\n"
        "PERSON COLUMNS RULE: Whenever a query involves people (users, students, instructors, etc.), "
        "always include the following columns as the FIRST selected columns, in this exact order, "
        "if they are available in the table:\n"
        "  1. The person's ID (e.g. id, user_id, student_id — whichever is the primary key)\n"
        "  2. Full name as a single concatenated column: first_name || ' ' || last_name AS full_name\n"
        "  3. Email address (e.g. email)\n"
        "After these three, include any other columns that are specifically relevant to the user's query. "
        "If any of these three columns do not exist in the table, omit them.\n\n"
        "OUTPUT FORMAT — CRITICAL: Your ENTIRE response must consist of EXACTLY these three sections, "
        "each appearing EXACTLY ONCE, in this exact order. "
        "Do NOT repeat any section. Do NOT output any text before ### Business Interpretation. "
        "Do NOT add any other headings, sections, preamble, closing remarks, or commentary. "
        "Do NOT output thinking, reasoning, assumptions, or planning text.\n\n"
        "### Business Interpretation\n"
        "[Plain-language explanation of what the user is asking and what the query will return.]\n\n"
        "### SQL Query\n"
        "```sql\n[The complete SQL query — write it once and stop]\n```\n\n"
        "### How to Interpret the Results\n"
        "[Concise guidance on how to read and act on the query results — write it once and stop]\n\n"
        "Be very polite and answer as IDI."
    )
    extra_context = load_context()
    if extra_context:
        system_content += "\n\n### DATABASE CONTEXT:\n" + extra_context
    return system_content


# ── chat endpoint ─────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    history: list = []


@app.post("/chat")
def chat(req: ChatRequest):
    if not req.message:
        return JSONResponse({"error": "No message provided"}, status_code=400)

    messages = [{"role": "system", "content": build_system_prompt()}]
    messages.extend(req.history)
    messages.append({"role": "user", "content": req.message})

    payload = {"messages": messages, "temperature": 0.7}

    try:
        t0 = time.time()
        response = requests.post(LLAMA_CPP_SERVER_URL, json=payload, timeout=60)
        response.raise_for_status()
        t1 = time.time()

        result = response.json()
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        usage = result.get("usage", {})

        metrics = {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "time_ms": int((t1 - t0) * 1000),
        }
        return {"response": content, "metrics": metrics}

    except requests.exceptions.Timeout:
        return JSONResponse(
            {"error": "The model took too long to respond. Try a shorter query."},
            status_code=504,
        )
    except requests.exceptions.ConnectionError:
        return JSONResponse(
            {"error": f"Could not reach the llama.cpp server at {LLAMA_CPP_SERVER_URL}. "
                      "Is it running? Start it with: python sandbox/sandbox_app.py"},
            status_code=503,
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ── benchmark definitions ─────────────────────────────────────────────────────

BENCHMARK_QUERIES = [
    {
        "id": "mid-level",
        "title": "Mid-Level — JOIN + Aggregation + Filter",
        "query": "Who are the top 3 instructors generating the most revenue from 'advanced' courses?",
        "key_tables": ["users", "courses", "payments"],
        "key_keywords": ["JOIN", "SUM", "GROUP BY", "ORDER BY", "LIMIT", "WHERE"],
    },
    {
        "id": "simple",
        "title": "Simple — JOIN + AVG + ORDER BY",
        "query": "What are the top 5 highest-rated courses and who teaches them?",
        "key_tables": ["courses", "users", "reviews"],
        "key_keywords": ["JOIN", "AVG", "GROUP BY", "ORDER BY", "LIMIT"],
    },
    {
        "id": "subquery",
        "title": "Subquery — NOT EXISTS + Date Filter",
        "query": "Which students have not submitted any assignment before its due date?",
        "key_tables": ["users", "enrollments", "assignments", "submissions"],
        "key_keywords": ["JOIN", "NOT EXISTS", "WHERE", "DISTINCT"],
    },
    {
        "id": "cte-window",
        "title": "CTE + Window — RANK() over Category",
        "query": "For each course category, which course has the highest completion rate?",
        "key_tables": ["courses", "course_categories", "enrollments"],
        "key_keywords": ["WITH", "RANK", "OVER", "PARTITION BY", "JOIN", "GROUP BY"],
    },
    {
        "id": "analytical",
        "title": "Analytical — Date Aggregation + Refund Rate",
        "query": (
            "Show me the monthly revenue breakdown for the last 6 months, "
            "including the number of transactions and the refund rate."
        ),
        "key_tables": ["payments"],
        "key_keywords": ["DATE_FORMAT", "GROUP BY", "ORDER BY", "SUM", "COUNT", "WHERE"],
    },
]


# ── correctness scoring ───────────────────────────────────────────────────────

def score_correctness(generated_response: str, query_def: dict) -> dict:
    """
    Lightweight correctness check: extract the SQL block from the response and
    verify that key tables + keywords from the reference are present.
    Returns a 0-100 score and detail lists.
    """
    sql_match = re.search(r"```sql\s*([\s\S]*?)```", generated_response, re.IGNORECASE)
    if not sql_match:
        return {
            "score": 0,
            "has_sql": False,
            "found_tables": [],
            "missing_tables": list(query_def["key_tables"]),
            "found_keywords": [],
            "missing_keywords": list(query_def["key_keywords"]),
        }

    generated_sql = sql_match.group(1).upper()
    key_tables = [t.upper() for t in query_def["key_tables"]]
    key_keywords = [k.upper() for k in query_def["key_keywords"]]

    found_tables = [t for t in key_tables if t in generated_sql]
    found_keywords = [k for k in key_keywords if k in generated_sql]

    table_score = len(found_tables) / len(key_tables) if key_tables else 1.0
    kw_score = len(found_keywords) / len(key_keywords) if key_keywords else 1.0
    overall = round((table_score * 0.6 + kw_score * 0.4) * 100)

    return {
        "score": overall,
        "has_sql": True,
        "found_tables": found_tables,
        "missing_tables": [t for t in key_tables if t not in found_tables],
        "found_keywords": found_keywords,
        "missing_keywords": [k for k in key_keywords if k not in found_keywords],
    }


# ── llama.cpp process management ─────────────────────────────────────────────

def _find_llama_server() -> str | None:
    root = SANDBOX_ROOT
    local_candidates = [
        os.path.join(root, "llama.cpp", "build", "bin", "Release", "llama-server.exe"),
        os.path.join(root, "llama.cpp", "build", "bin", "llama-server"),
        os.path.join(root, "llama.cpp", "llama-server.exe"),
    ]
    for path in local_candidates:
        if os.path.isfile(path):
            return path

    local_app = os.environ.get("LOCALAPPDATA", "")
    winget_bin = os.path.join(
        local_app, "Microsoft", "WinGet", "Packages",
        "ggml.llamacpp_Microsoft.Winget.Source_8wekyb3d8bbwe",
        "llama-server.exe",
    )
    if os.path.isfile(winget_bin):
        return winget_bin

    return shutil.which("llama-server") or shutil.which("llama-server.exe")


def _kill_process_on_port(port: int) -> bool:
    """Kill the process(es) listening on the given TCP port."""
    killed = False
    if HAS_PSUTIL:
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                for conn in proc.net_connections(kind="inet"):
                    if conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
                        proc.kill()
                        killed = True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    else:
        # Fallback: Windows netstat approach
        if sys.platform == "win32":
            out = subprocess.run(
                ["netstat", "-ano"], capture_output=True, text=True
            ).stdout
            for line in out.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.split()
                    pid = parts[-1]
                    subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True)
                    killed = True
    return killed


def _llama_healthy(port: int = int(LLAMA_PORT), timeout: int = 2) -> bool:
    try:
        import urllib.request
        with urllib.request.urlopen(
            f"http://localhost:{port}/health", timeout=timeout
        ) as r:
            return r.status == 200
    except Exception:
        return False


def _wait_for_llama(port: int = int(LLAMA_PORT), timeout_s: int = 90) -> bool:
    for _ in range(timeout_s):
        if _llama_healthy(port):
            return True
        time.sleep(1)
    return False


def _switch_llama_mode(ngl: int, job: dict) -> bool:
    """Kill the running llama.cpp server and restart it with the given -ngl value."""
    port = int(LLAMA_PORT)
    binary = _find_llama_server()
    model = MODEL_PATH

    if not binary:
        job["mode_error"] = "llama-server binary not found."
        return False
    if not os.path.isfile(model):
        job["mode_error"] = f"Model not found at: {model}"
        return False

    job["stage_label"] = f"Stopping llama.cpp server on port {port}…"
    _kill_process_on_port(port)
    time.sleep(3)  # give the OS time to release the port

    mode_label = "GPU (ngl=99)" if ngl >= 99 else "CPU (ngl=0)"
    job["stage_label"] = f"Starting llama.cpp in {mode_label} mode…"

    log_path = os.path.join(SANDBOX_ROOT, "llama_server.log")
    with open(log_path, "a") as log_f:
        subprocess.Popen(
            [binary, "--model", model, "--port", str(port), "-ngl", str(ngl)],
            stdout=log_f,
            stderr=log_f,
        )

    job["stage_label"] = "Waiting for llama.cpp to become healthy…"
    if not _wait_for_llama(port, timeout_s=90):
        job["mode_error"] = "llama.cpp did not become healthy within 90 s."
        return False

    job["stage_label"] = f"llama.cpp ready in {mode_label} mode."
    return True


# ── benchmark job store ───────────────────────────────────────────────────────

_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()


def _run_benchmark_task(job_id: str, mode: str) -> None:
    with _jobs_lock:
        job = _jobs.get(job_id)
    if job is None:
        return

    ngl = 99 if mode == "gpu" else 0
    system_prompt = build_system_prompt()

    # 1. Switch mode
    job["phase"] = "switching"
    ok = _switch_llama_mode(ngl, job)
    if not ok:
        job["status"] = "error"
        job["error"] = job.get("mode_error", "Failed to switch llama.cpp mode.")
        return

    # 2. Run all queries
    job["phase"] = "running"
    results = []
    total = len(BENCHMARK_QUERIES)

    for idx, q in enumerate(BENCHMARK_QUERIES):
        job["stage_label"] = f"Running query {idx + 1}/{total}: {q['title']}"
        job["progress"] = idx

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": q["query"]},
        ]
        payload = {"messages": messages, "temperature": 0.1}

        try:
            t0 = time.time()
            resp = requests.post(LLAMA_CPP_SERVER_URL, json=payload, timeout=180)
            resp.raise_for_status()
            t1 = time.time()

            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            usage = data.get("usage", {})

            correctness = score_correctness(content, q)

            results.append({
                "id": q["id"],
                "title": q["title"],
                "query": q["query"],
                "response": content,
                "metrics": {
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "time_ms": int((t1 - t0) * 1000),
                },
                "correctness": correctness,
                "error": None,
            })
        except Exception as e:
            results.append({
                "id": q["id"],
                "title": q["title"],
                "query": q["query"],
                "response": "",
                "metrics": None,
                "correctness": {"score": 0, "has_sql": False,
                                "found_tables": [], "missing_tables": q["key_tables"],
                                "found_keywords": [], "missing_keywords": q["key_keywords"]},
                "error": str(e),
            })

    job["progress"] = total
    job["results"] = results
    job["status"] = "done"
    job["stage_label"] = "Benchmark complete."


# ── benchmark endpoints ───────────────────────────────────────────────────────

class BenchmarkStartRequest(BaseModel):
    mode: str = "gpu"  # "gpu" | "cpu"


@app.post("/benchmark/start")
def benchmark_start(req: BenchmarkStartRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    job: dict = {
        "id": job_id,
        "mode": req.mode,
        "status": "running",
        "phase": "init",
        "stage_label": "Initialising…",
        "progress": 0,
        "total": len(BENCHMARK_QUERIES),
        "results": [],
        "error": None,
    }
    with _jobs_lock:
        _jobs[job_id] = job
    background_tasks.add_task(_run_benchmark_task, job_id, req.mode)
    return {"job_id": job_id}


@app.get("/benchmark/status/{job_id}")
def benchmark_status(job_id: str):
    with _jobs_lock:
        job = _jobs.get(job_id)
    if job is None:
        return JSONResponse({"error": "Job not found"}, status_code=404)
    return job


@app.get("/benchmark/llama-healthy")
def benchmark_llama_healthy():
    return {"healthy": _llama_healthy()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
