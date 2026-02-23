# Sandbox application for testing the Qwen2.5-Coder-3B-Instruct model via llama.cpp

import requests
import os
import subprocess
import threading
import sys
import time
import re

# ANSI Color Codes
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def format_model_response(text):
    """Formats the model response with colors for SQL blocks."""
    # Colorize SQL code blocks
    def replace_sql(match):
        return f"{Colors.YELLOW}{match.group(0)}{Colors.RESET}"
    
    # Regex to find markdown SQL blocks (```sql ... ```)
    formatted_text = re.sub(r'```sql.*?```', replace_sql, text, flags=re.DOTALL)
    
    # Also colorize inline code if needed, or just keep it simple
    return formatted_text

def start_llama_cpp_server():
    """Start the llama.cpp server with the specified model and configuration."""
    sandbox_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Define absolute paths
    model_relative = os.getenv("LLAMA_CPP_MODEL_PATH", "llama.cpp/models/qwen2.5-coder-3b-instruct-q4_k_m.gguf")
    model_path = os.path.join(sandbox_dir, model_relative)
    server_port = os.getenv("LLAMA_CPP_SERVER_PORT", "7860")
    # Prefer cmake-built binary; fall back to legacy pre-built location
    cmake_binary_win = os.path.join(sandbox_dir, "llama.cpp", "build", "bin", "Release", "llama-server.exe")
    cmake_binary_unix = os.path.join(sandbox_dir, "llama.cpp", "build", "bin", "llama-server")
    legacy_binary = os.path.join(sandbox_dir, "llama.cpp", "llama-server.exe")
    local_binary = cmake_binary_win if os.path.exists(cmake_binary_win) \
        else cmake_binary_unix if os.path.exists(cmake_binary_unix) \
        else legacy_binary
    log_file_path = os.path.join(sandbox_dir, "llama_server.log")

    # Check if the server is already running
    try:
        response = requests.get(f"http://localhost:{server_port}/health", timeout=2)
        if response.status_code == 200:
            return
    except requests.exceptions.RequestException:
        pass

    # Determine binary to run (Local Priority)
    binary_to_run = "llama-server"
    if os.path.exists(local_binary):
        binary_to_run = local_binary
        print(f"{Colors.CYAN}Using local llama.cpp binary: {local_binary}{Colors.RESET}")
    else:
        print(f"{Colors.CYAN}Local binary not found, attempting to use global 'llama-server'...{Colors.RESET}")

    if not os.path.exists(model_path):
        print(f"{Colors.RED}Error: Model not found at {model_path}{Colors.RESET}")
        print(f"{Colors.YELLOW}Please ensure you downloaded the model and placed it in the correct folder.{Colors.RESET}")
        sys.exit(1)

    print(f"{Colors.CYAN}Starting llama.cpp server in background...{Colors.RESET}")
    print(f"{Colors.CYAN}Logs will be written to: {log_file_path}{Colors.RESET}")
    
    with open(log_file_path, "w") as log_file:
        subprocess.Popen(
            [binary_to_run, "--model", model_path, "--port", server_port],
            stdout=log_file,
            stderr=log_file,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
        )

    # Wait for the server to be healthy
    print(f"{Colors.YELLOW}Waiting for server to become healthy...{Colors.RESET}")
    max_retries = 30
    for i in range(max_retries):
        try:
            response = requests.get(f"http://localhost:{server_port}/health", timeout=2)
            if response.status_code == 200:
                print(f"{Colors.GREEN}Server is healthy and ready!{Colors.RESET}")
                return
        except requests.exceptions.RequestException:
            pass
        
        sys.stdout.write(f"\r{Colors.YELLOW}Retry {i+1}/{max_retries}...{Colors.RESET}")
        sys.stdout.flush()
        time.sleep(1)
    
    print(f"\n{Colors.RED}Error: Server failed to start or become healthy after {max_retries} seconds.{Colors.RESET}")
    print(f"{Colors.YELLOW}Check {log_file_path} for details.{Colors.RESET}")
    sys.exit(1)

def main():
    # Enable VT100 emulation in Windows console (needed for colors)
    os.system('') 
    
    print(f"{Colors.HEADER}Welcome to IDI (Intelligent Database Interface) Sandbox!{Colors.RESET}")
    print(f"{Colors.CYAN}Model: Qwen2.5-Coder-3B-Instruct{Colors.RESET}")
    print("Type your query below (type 'exit' to quit):")

    # Start the llama.cpp server
    start_llama_cpp_server()

    # Load llama.cpp server URL from environment variable or use default
    llama_cpp_server_url = os.getenv("LLAMA_CPP_SERVER_URL", "http://localhost:7860/v1/chat/completions")

    def load_context():
        """Reads all files in sandbox/context/ and returns their content."""
        context_dir = os.path.join(os.path.dirname(__file__), "context")
        combined_context = ""
        if os.path.exists(context_dir):
            for filename in os.listdir(context_dir):
                file_path = os.path.join(context_dir, filename)
                if os.path.isfile(file_path):
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            combined_context += f"\n\n--- Context from {filename} ---\n"
                            combined_context += f.read()
                    except Exception as e:
                        print(f"{Colors.RED}Warning: Could not read {filename}: {e}{Colors.RESET}")
        return combined_context

    # Initialize chat history
    chat_history = []

    while True:
        # User input in BLUE
        try:
            user_input = input(f"\n{Colors.BLUE}You: {Colors.RESET}")
        except KeyboardInterrupt:
            print("\nExiting...")
            break

        if user_input.lower() == "exit":
            print(f"{Colors.CYAN}Exiting the sandbox. Goodbye!{Colors.RESET}")
            break
        
        # Add user input to history
        chat_history.append({"role": "user", "content": user_input})

        # Reload context on every turn to allow dynamic updates
        extra_context = load_context()
        
        # Construct the messages list
        # 1. System Prompt
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
            "Be very polite and answer as IDI."
        )
        if extra_context:
            system_content += "\n\n### DATABASE CONTEXT:\n" + extra_context
            
        # Construct the verified system prompt
        base_messages = [{"role": "system", "content": system_content}]
        base_messages.extend(chat_history)

        def get_completion_with_timer(messages, prefix_text="Processing", start_time=None):
            """Helper to call llama.cpp server with valid timer animation"""
            stop_animation = threading.Event()
            
            if start_time is None:
                start_time = time.time()

            def animate():
                while not stop_animation.is_set():
                    elapsed = time.time() - start_time
                    dots = int(elapsed * 2) % 4
                    # \033[K clears the line
                    sys.stdout.write(f"\r\033[K{Colors.HEADER}[ {elapsed:5.1f}s ] {prefix_text}{'.' * dots}{Colors.RESET}")
                    sys.stdout.flush()
                    stop_animation.wait(0.1)

            animation_thread = threading.Thread(target=animate)
            animation_thread.start()

            try:
                response = requests.post(
                    llama_cpp_server_url,
                    json={"messages": messages, "temperature": 0.7}
                )
                stop_animation.set()
                animation_thread.join()
                
                # Clear the timer line after completion
                sys.stdout.write(f"\r\033[K")
                sys.stdout.flush()

                response.raise_for_status()
                result = response.json()
                return result.get("choices", [{}])[0].get("message", {}).get("content", "")
            except Exception as e:
                stop_animation.set()
                animation_thread.join()
                print(f"\n{Colors.RED}Error: {e}{Colors.RESET}")
                return None

        # Execute simple chat completion
        sys.stdout.write(f"{Colors.HEADER}Generating...{Colors.RESET}")
        sys.stdout.flush()
        
        start_time = time.time()
        final_content = get_completion_with_timer(base_messages, "Generating", start_time)
        
        if not final_content:
            continue

        total_elapsed = time.time() - start_time
        print(f"{Colors.GREEN}>> Complete in {total_elapsed:.1f}s{Colors.RESET}\n")

        # Format and print model response
        print(f"{Colors.GREEN}IDI:{Colors.RESET}")
        print(format_model_response(final_content))
        
        # Add response to history
        chat_history.append({"role": "assistant", "content": final_content})

        # Feedback Loop
        while True:
            try:
                feedback = input(f"\n{Colors.YELLOW}Feedback (Enter to continue, or type to refine): {Colors.RESET}")
            except KeyboardInterrupt:
                break
                
            if not feedback.strip():
                break
            
            # Add feedback to history
            chat_history.append({"role": "user", "content": f"Feedback: {feedback}. Please regenerate the previous response based on this feedback."})
            
            # Construct messages with feedback
            messages = [{"role": "system", "content": system_content}]
            messages.extend(chat_history)
            
            # Generate refined response
            refined_response = get_completion_with_timer(messages, "Refining")
            
            if refined_response:
                print(f"{Colors.GREEN}IDI (Refined):{Colors.RESET}")
                print(format_model_response(refined_response))
                chat_history.append({"role": "assistant", "content": refined_response})
            else:
                break



if __name__ == "__main__":
    main()