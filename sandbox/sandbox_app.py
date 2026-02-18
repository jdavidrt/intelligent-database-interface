# Sandbox application for testing models and LoRA adapters

from fastapi import FastAPI
from pydantic import BaseModel
import subprocess

# Initialize FastAPI app
app = FastAPI()

# Define a request model
class QueryRequest(BaseModel):
    query: str

# Endpoint to test the model with a query
@app.post("/test_model")
async def test_model(request: QueryRequest):
    # Simulate model testing (replace with actual model inference code)
    try:
        # Example: Call a subprocess to run the model with the given query
        result = subprocess.run(
            ["python", "../backend/sql_generator.py", request.query],
            capture_output=True,
            text=True
        )
        return {"query": request.query, "result": result.stdout}
    except Exception as e:
        return {"error": str(e)}

# Example root endpoint
@app.get("/")
async def root():
    return {"message": "Welcome to the sandbox for testing models and LoRA adapters!"}