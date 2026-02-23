# Minimal Backend Implementation Plan (Sandbox)

The backend will be a simple Python Flask application that provides an API endpoint for the frontend to interact with the LLM (via the `llama.cpp` server).

## Proposed Changes

### [NEW] [app.py](file:///c:/Users/jdk_l/OneDrive/Documents/UNAL/IDI/repo/intelligent-database-interface/sandbox/backend/app.py)

- Create a Flask server with a `/chat` POST endpoint.
- The endpoint will receive a user query, forward it to the `llama.cpp` server (reusing logic from `sandbox_app.py`), and return the JSON response.
- Use `flask-cors` to allow requests from the frontend.

## Verification Plan

### Automated Tests
- Send a POST request to `http://localhost:5000/chat` using `curl` or a tool like Postman and verify a valid response from the LLM.
