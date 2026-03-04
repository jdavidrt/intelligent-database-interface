from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import time
import requests
import os

app = FastAPI(title="IDI Sandbox Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# llama.cpp server configuration
LLAMA_CPP_SERVER_URL = os.getenv("LLAMA_CPP_SERVER_URL", "http://localhost:7860/v1/chat/completions")

# Path to the context directory (same as sandbox_app.py uses)
CONTEXT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "context")


def load_context() -> str:
    """Read all files in sandbox/context/ and return their combined content."""
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
    """Construct the full IDI system prompt, same as sandbox_app.py."""
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


class ChatRequest(BaseModel):
    message: str
    history: list = []


@app.post("/chat")
def chat(req: ChatRequest):
    if not req.message:
        return JSONResponse({"error": "No message provided"}, status_code=400)

    # Build messages: system + history + new user message
    messages = [{"role": "system", "content": build_system_prompt()}]
    messages.extend(req.history)
    messages.append({"role": "user", "content": req.message})

    payload = {
        "messages": messages,
        "temperature": 0.7,
    }

    try:
        t0 = time.time()
        response = requests.post(LLAMA_CPP_SERVER_URL, json=payload, timeout=60)
        response.raise_for_status()
        t1 = time.time()

        result = response.json()
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        usage = result.get("usage", {})
        
        print(f"DEBUG LLM RESULT: {result}")
        print(f"DEBUG USAGE: {usage}")

        metrics = {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "time_ms": int((t1 - t0) * 1000)
        }
        
        print(f"DEBUG METRICS TO FRONTEND: {metrics}")
        
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
