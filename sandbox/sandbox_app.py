# Sandbox application for testing Qwen2.5-Coder-3B-Instruct model via text input

import requests

def main():
    print("Welcome to the Qwen2.5-Coder-3B-Instruct Sandbox!")
    print("Type your query below (type 'exit' to quit):")

    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            print("Exiting the sandbox. Goodbye!")
            break

        try:
            # Send the query to the llama.cpp server
            response = requests.post(
                "http://localhost:8080/generate",  # Replace with actual llama.cpp server endpoint
                json={"prompt": user_input}
            )
            response.raise_for_status()
            result = response.json()
            print("Model:", result)
        except requests.exceptions.RequestException as e:
            print("Error communicating with the model:", e)

if __name__ == "__main__":
    main()