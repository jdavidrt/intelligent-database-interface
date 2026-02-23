from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

# llama.cpp server configuration
LLAMA_CPP_SERVER_URL = os.getenv("LLAMA_CPP_SERVER_URL", "http://localhost:7860/v1/chat/completions")

# Reuse the same context directory as the sandbox so responses are identical
CONTEXT_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "sandbox", "context"
)


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
    """Construct the full IDI system prompt from context files.

    The SYSTEM_PROMPT.md inside sandbox/context/ contains the enterprise-grade
    NL2SQL rules. Loading it here gives backend/app.py the same behaviour as
    the sandbox without duplicating content.
    """
    # Base identity (fallback if SYSTEM_PROMPT.md is absent)
    base = (
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
        "Be very polite and answer as IDI."
    )

    extra_context = load_context()
    if extra_context:
        # If SYSTEM_PROMPT.md was loaded it already contains the full rules;
        # prepend a short identity line so the model still knows its name.
        system_content = "You are IDI (Intelligent Database Interface).\n" + extra_context
    else:
        system_content = base

    return system_content


@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message')
    chat_history = data.get('history', [])

    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    messages = [{"role": "system", "content": build_system_prompt()}]
    messages.extend(chat_history)
    messages.append({"role": "user", "content": user_message})

    payload = {
        "messages": messages,
        "temperature": 0.7,
    }

    try:
        response = requests.post(LLAMA_CPP_SERVER_URL, json=payload, timeout=120)
        response.raise_for_status()
        result = response.json()
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        return jsonify({"response": content})
    except requests.exceptions.Timeout:
        return jsonify({"error": "The model took too long to respond. Try a shorter query."}), 504
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(port=5001, debug=True)
