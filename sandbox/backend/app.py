from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

# llama.cpp server configuration
LLAMA_CPP_SERVER_URL = os.getenv("LLAMA_CPP_SERVER_URL", "http://localhost:7860/v1/chat/completions")

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message')
    
    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    # For a minimal version, we'll just send a simple chat completion request
    # No complex history or context for this "minimum working" component
    payload = {
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": user_message}
        ],
        "temperature": 0.7
    }

    try:
        response = requests.post(LLAMA_CPP_SERVER_URL, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        return jsonify({"response": content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000, debug=True)
