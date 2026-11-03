import os
import sys
import re
import subprocess
from google import genai
from google.genai import types

# Initialize the Gemini Client
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("❌ Error: GEMINI_API_KEY environment variable not found.")
    print("Please run this in your terminal first: export GEMINI_API_KEY='your_key'")
    sys.exit(1)

client = genai.Client(api_key=api_key)
MODEL_ID = "gemini-2.5-flash"  # Free, high-quality reasoning model

WORKSPACE_DIR = "./agent_workspace"
os.makedirs(WORKSPACE_DIR, exist_ok=True)

SYSTEM_PROMPT = """You are an elite, autonomous software engineering agent. Your objective is to fulfill the user's task by writing code, executing it, analyzing results, and fixing your own bugs.

You operate inside a workspace folder: './agent_workspace/'

To perform actions, you MUST structure your response exactly like this:

THOUGHT: Describe your deep reasoning, architecture planning, or debugging strategy.

FILEPATH: agent_workspace/your_script.py

CODE:
```python
# Your full code goes here (HTML, Python, Javascript, etc.)
```

TEST_COMMAND: python3 agent_workspace/your_script.py

Rules:
1. Always output the FULL rewritten file inside the CODE block. No snippets or placeholder comments like '# ... rest of code'.
2. The TEST_COMMAND must be a command that executes your code to prove it works.
3. If you are generating a web page (like index.html), your TEST_COMMAND can just check if the file exists or run a syntax validator.
"""

def clean_ai_text(text):
    """Normalizes formatting line endings and spaces for cleaner parsing."""
    return text.replace("\(\r\\)n", "\n").strip()

def run_agent_loop(user_goal):
    print(f"🚀 Initializing Autonomous Agent...")
    print(f"🎯 Objective: {user_goal}\n")
    
    # Setup conversation tracking
    chats = [
        types.Content(role="user", parts=[types.Part.from_text(text=f"System Instructions:\n{SYSTEM_PROMPT}\n\nUser Task: {user_goal}")])
    ]
    
    max_iterations = 7  # Maximum healing cycles
    
    for iteration in range(1, max_iterations + 1):
        print(f"⚡ --- Iteration {iteration}/{max_iterations} ---")
        print("🧠 Thinking...")
        
        try:
            response = client.models.generate_content(
                model=MODEL_ID,
                contents=chats,
                config=types.GenerateContentConfig(
                    temperature=0.1,  # Low temperature forces precise, deterministic logic
                )
            )
        except Exception as e:
            print(f"❌ API Communication Error: {e}")
            break
            
        ai_response = response.text
        chats.append(types.Content(role="model", parts=[types.Part.from_text(text=ai_response)]))
        
        # Parse output using regular expressions
        ai_normalized = clean_ai_text(ai_response)
        
        filepath_match = re.search(r"FILEPATH:\s*([^\n]+)", ai_normalized)
        code_match = re.search(r"CODE:\n```[a-zA-Z]*\n(.*?)```", ai_normalized, re.DOTALL)
        test_match = re.search(r"TEST_COMMAND:\s*([^\n]+)", ai_normalized)
        
        if not filepath_match or not code_match or not test_match:
            print("⚠️ Parsing mismatch. The AI strayed from the format. Requesting correction...")
            error_msg = "Error: Your formatting did not match the strict schema. You must provide FILEPATH, CODE blocks, and a TEST_COMMAND exactly as instructed."
            chats.append(types.Content(role="user", parts=[types.Part.from_text(text=error_msg)]))
            continue
            
        filepath = filepath_match.group(1).strip()
        code_content = code_match.group(1)
        test_command = test_match.group(1).strip()
        
        # Step 1: Write the generated file
        print(f"📝 Writing autonomous asset: {filepath}")
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(code_content)
        except Exception as e:
            error_msg = f"File Write Error: Could not write to {filepath}. Reason: {e}"
            chats.append(types.Content(role="user", parts=[types.Part.from_text(text=error_msg)]))
            continue
            
        # Step 2: Run automated verification
        print(f"💻 Executing verification: `{test_command}`")
        result = subprocess.run(test_command, shell=True, capture_output=True, text=True)
        
        # Step 3: Evaluate performance metrics
        if result.returncode == 0:
            print("\n🎉 Success! The code executed perfectly with zero exit errors.")
            print(f"📊 Execution Output:\n{result.stdout}")
            break
        else:
            print(f"⚠️ Validation failure detected (Exit Code: {result.returncode}).")
            print("🩺 Transferring crash logs back to the core brain for self-healing...")
            
            feedback_payload = (
                f"Execution Failed.\n"
                f"Command Run: {test_command}\n"
                f"Exit Code: {result.returncode}\n"
                f"STDOUT:\n{result.stdout}\n"
                f"STDERR:\n{result.stderr}\n"
                f"Please diagnose the crash, modify your logic, rewrite the script entirely, and re-test."
            )
            chats.append(types.Content(role="user", parts=[types.Part.from_text(text=feedback_payload)]))
            
    else:
        print("\n❌ Process halted: Reached max safe iterations without absolute stability.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage Error: Please supply an explicit task description.")
        print("Example: python3 agent.py 'Create a python password generator utility'")
        sys.exit(1)
        
    task_input = " ".join(sys.argv[1:])
    run_agent_loop(task_input)
