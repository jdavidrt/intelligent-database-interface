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
    model_path = os.getenv("LLAMA_CPP_MODEL_PATH", "llama.cpp/models/qwen2.5-coder-3b-instruct-q4_k_m.gguf")
    server_port = os.getenv("LLAMA_CPP_SERVER_PORT", "8080")

    # Check if the server is already running
    try:
        response = requests.get(f"http://localhost:{server_port}/health")
        if response.status_code == 200:
            # print("llama.cpp server is already running.")
            return
    except requests.exceptions.RequestException:
        pass

    # Start the server (llama-server installed via winget is available system-wide)
    print(f"{Colors.CYAN}Starting llama.cpp server...{Colors.RESET}")
    subprocess.Popen(
        ["llama-server", "--model", model_path, "--port", server_port],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    print(f"{Colors.GREEN}llama.cpp server started on port {server_port}.{Colors.RESET}")

def main():
    # Enable VT100 emulation in Windows console (needed for colors)
    os.system('') 
    
    print(f"{Colors.HEADER}Welcome to IDI (Intelligent Database Interface) Sandbox!{Colors.RESET}")
    print(f"{Colors.CYAN}Model: Qwen2.5-Coder-3B-Instruct{Colors.RESET}")
    print("Type your query below (type 'exit' to quit):")

    # Start the llama.cpp server
    start_llama_cpp_server()

    # Load llama.cpp server URL from environment variable or use default
    llama_cpp_server_url = os.getenv("LLAMA_CPP_SERVER_URL", "http://localhost:8080/v1/chat/completions")

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
        system_content = "You are IDI (Intelligent Database Interface) a NL to SQL model, you should answer as IDI and be very polite."
        if extra_context:
            system_content += "\n\nUse the following context to answer the user's request:" + extra_context
            
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

        def run_timed_interaction(initial_messages, phase_name, min_duration=30):
            """Loops the model interaction for a minimum duration."""
            start_time = time.time()
            current_messages = initial_messages.copy()
            
            # Initial generation
            print(f"{Colors.CYAN}Starting {phase_name} Phase ({min_duration}s minimum)...{Colors.RESET}")
            content = get_completion_with_timer(current_messages, f"{phase_name} (Initial)", start_time)
            if not content: return None

            iteration = 1
            while (time.time() - start_time) < min_duration:
                elapsed = time.time() - start_time
                remaining = max(0, min_duration - elapsed)
                
                # Append the previous assistant output
                current_messages.append({"role": "assistant", "content": content})
                
                # Prompt for refinement
                refine_prompt = f"You have {remaining:.1f} seconds remaining in the {phase_name} phase. Critically review your last response. Improve accuracy, check for edge cases, and refine logic. Output the improved version."
                current_messages.append({"role": "user", "content": refine_prompt})
                
                # Generate refinement
                new_content = get_completion_with_timer(current_messages, f"{phase_name} (Iter {iteration})", start_time)
                if new_content:
                    content = new_content
                iteration += 1

            print(f"{Colors.GREEN}>> {phase_name} Complete in {time.time() - start_time:.1f}s{Colors.RESET}\n")
            return content

        # --- PHASE 1: DEEP THINKING (30s) ---
        # Ask for a reasoning plan first
        think_messages = base_messages.copy()
        think_messages.append({
            "role": "user", 
            "content": "Phase 1: Deep Thinking. logic only. Do NOT generate SQL yet. Analyze the Request, Schema, and Strategy. Critique your own logic."
        })
        
        thought_process = run_timed_interaction(think_messages, "Thinking", min_duration=30)
        if not thought_process: continue

        # --- PHASE 2: SQL GENERATION ---
        # Now ask for SQL based on the refined thought
        print(f"{Colors.CYAN}Generating SQL Draft...{Colors.RESET}")
        gen_messages = base_messages.copy()
        gen_messages.append({"role": "assistant", "content": thought_process}) # Contextualize with best thought
        gen_messages.append({"role": "user", "content": "Now, based on that analysis, generate the single optimized MySQL SELECT statement."})
        
        sql_draft = get_completion_with_timer(gen_messages, "Drafting SQL")
        if not sql_draft: continue

        # --- PHASE 3: FINAL VALIDATION (30s) ---
        # Validate the SQL
        verify_messages = base_messages.copy()
        verify_messages.append({"role": "assistant", "content": sql_draft})
        verify_messages.append({
            "role": "user", 
            "content": "Phase 3: Validation. Check syntax, table names, joins, and logic. If errors found, fix them. If optimal, confirm it."
        })
        
        final_content = run_timed_interaction(verify_messages, "Validation", min_duration=30) or sql_draft

        # Format and print model response
        print(f"{Colors.GREEN}IDI:{Colors.RESET}")
        print(format_model_response(final_content))
        
        # Add FINAL verified response to history (keeping context clean)
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