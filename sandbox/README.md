# Sandbox Deployment Instructions

This sandbox is designed to test the Qwen2.5-Coder-3B-Instruct model in a local environment.

## Prerequisites

1. Install Python 3.10 or higher.
2. Install the required dependencies by running:

   ```bash
   pip install fastapi uvicorn pydantic requests
   ```

3. Ensure that the Qwen2.5-Coder-3B-Instruct model is properly set up and the `llama.cpp` server is running locally.
   - The server should be accessible at `http://localhost:8080`.
   - Follow the `llama.cpp` documentation to set up and start the server.

## Running the Sandbox

1. Navigate to the `sandbox` directory:

   ```bash
   cd sandbox
   ```

2. Start the FastAPI application using Uvicorn:

   ```bash
   uvicorn sandbox_app:app --reload --host 0.0.0.0 --port 8001
   ```

3. Open your browser and navigate to `http://127.0.0.1:8001` to access the sandbox.

4. Use the `/test_model` endpoint to test the Qwen2.5-Coder-3B-Instruct model. You can send a POST request with a JSON payload containing the `query` field.

   Example payload:

   ```json
   {
     "query": "SELECT * FROM users WHERE age > 30"
   }
   ```

   You can use tools like [Postman](https://www.postman.com/) or `curl` to send requests.

## Notes

- Ensure that the Qwen2.5-Coder-3B-Instruct model is properly downloaded and the `llama.cpp` server is running before starting the sandbox.
- Replace the placeholder code in `sandbox_app.py` with any additional model-specific logic if needed.
- The sandbox is designed to interact with the model via the `llama.cpp` server's HTTP API.
