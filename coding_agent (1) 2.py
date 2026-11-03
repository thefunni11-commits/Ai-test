import os
import subprocess
import json
from typing import List, Dict

# Configuration - Using Qwen2.5-Coder via local Ollama instance
# Ensure Ollama is running and you have run: ollama pull qwen2.5-coder:7b
MODEL_NAME = "qwen2.5-coder:7b"
OLLAMA_API_URL = "http://localhost:11434/api/generate"

def call_local_llm(prompt: str, system_prompt: str = "") -> str:
    """Helper to query the local Ollama instance safely using urllib."""
    import urllib.request
    
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "system": system_prompt,
        "stream": False,
        "options": {
            "temperature": 0.2  # Low temperature for stable, predictable code generation
        }
    }
    
    try:
        req = urllib.request.Request(
            OLLAMA_API_URL, 
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            return res_data.get("response", "")
    except Exception as e:
        return f"Error connecting to Ollama: {str(e)}. Please ensure Ollama is running (`ollama serve`)."

def run_terminal_command(command: str) -> tuple:
    """Executes a command safely inside the current working workspace."""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            text=True, 
            capture_output=True, 
            timeout=30
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out after 30 seconds."

def extract_code_block(llm_output: str) -> str:
    """Extracts the raw code block from the LLM's markdown wrapping."""
    if "```python" in llm_output:
        return llm_output.split("```python")[1].split("```")[0].strip()
    elif "```" in llm_output:
        return llm_output.split("```")[1].split("```")[0].strip()
    return llm_output.strip()

def autonomous_coding_loop(user_goal: str, target_file: str, test_command: str, max_iterations: int = 5):
    """The Core Autonomous loop: Plan -> Write -> Execute -> Evaluate -> Self-Correct."""
    print(f"🚀 Initializing Agent Task: {user_goal}")
    print(f"📂 Output File: {target_file} | 🛠️ Verification Command: {test_command}\n")
    
    history: List[Dict] = []
    current_error = "None. This is the first attempt. Write the full initial implementation."
    
    system_prompt = (
        "You are an expert autonomous Python software developer. Your goal is to write clean, production-ready "
        "Python code that matches the user request perfectly. Return ONLY the complete executable python code "
        "enclosed in ```python ... ``` markdown blocks. Do not include conversational preambles or explanations."
    )

    for iteration in range(1, max_iterations + 1):
        print(f"--- 🔄 Iteration {iteration}/{max_iterations} ---")
        
        # Build prompt containing the goal, current status, and past errors
        prompt = f"Goal: {user_goal}\nTarget File: {target_file}\n\n"
        if iteration > 1:
            prompt += f"Previous attempt failed. Feedback/Errors from execution:\n{current_error}\n\n"
            prompt += "Analyze the error carefully, fix the bug, and provide the fully updated, complete script."
        else:
            prompt += "This is the initial build. Generate the full script."

        print("🤖 AI is thinking & writing code...")
        llm_response = call_local_llm(prompt, system_prompt)
        clean_code = extract_code_block(llm_response)
        
        if "Error connecting to Ollama" in clean_code:
            print(f"❌ {clean_code}")
            return

        # Write code to filesystem
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(clean_code)
        print(f"💾 Code successfully written to {target_file}")

        # Execute code / Run validation tests
        print(f"⚙️ Running verification via: `{test_command}`...")
        return_code, stdout, stderr = run_terminal_command(test_command)
        
        if return_code == 0:
            print("\n==================================================")
            print("✅ SUCCESS! The autonomous agent built a stable application.")
            print(f"🎉 Verification output:\n{stdout}")
            print("==================================================")
            return
        else:
            print("⚠️ Verification failed. Error captured.")
            current_error = f"STDOUT:\n{stdout}\nSTDERR:\n{stderr}"
            print(f"Captured Error Context:\n{stderr or stdout}\n")
            
    print(f"❌ Completed {max_iterations} iterations without achieving a 0 return code. Review '{target_file}' manually.")

if __name__ == "__main__":
    # Example Scenario: Let's challenge the AI to create a fully functioning prime number generator
    # that handles error edge cases, and run it directly to check its validity.
    goal = "Create a robust python script containing a function `is_prime(n)` and print the first 15 prime numbers. Include brief error handling if numbers are negative."
    output_filename = "prime_runner.py"
    verification = "python3 prime_runner.py"
    
    autonomous_coding_loop(goal, output_filename, verification)
