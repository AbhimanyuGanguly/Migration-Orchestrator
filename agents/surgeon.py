import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from core.state import MigrationState
from tools.ast_modifier import apply_code_transformation

def modify_codebase(state: MigrationState) -> dict:
    test_stderr = state.get("test_stderr", "")
    migration_rules = state.get("migration_rules", [])
    retry_count = state.get("retry_count", 0)
    # Use work_dir (temp copy) instead of repo_path for all operations
    work_dir = state.get("work_dir", state.get("repo_path", ""))
    
    rules_str = "\n".join(migration_rules)
    
    system_prompt = SystemMessage(content="""You are a codebase surgeon. Your job is to fix failing tests caused by dependency migrations.
You are given the stderr from a failed pytest run and the migration rules for the dependency.
Identify the exact file and line failing.
Determine the fix based on the rules.
You MUST call the `apply_code_transformation` tool to repair it. Provide exact `old_code_snippet` and `new_code_snippet` strings.
IMPORTANT: Do NOT modify test files. Only modify source/library code.""")

    repo_context = state.get("repo_context", "")
    
    user_prompt = HumanMessage(content=f"""
Migration Rules:
{rules_str}

Test Stderr:
{test_stderr}

Repository Context (Current Code):
{repo_context}

Fix the code using the tool!
""")

    try:
        gemini_api_key = os.environ.get("GEMINI_API_KEY")
        llm = ChatGoogleGenerativeAI(
            model="gemini-3.8-flash",
            google_api_key=gemini_api_key,
            temperature=0,
            max_retries=3
        )
        llm_with_tools = llm.bind_tools([apply_code_transformation])
        response = llm_with_tools.invoke([system_prompt, user_prompt])
    except Exception as e:
        print(f"   ⚠️  Gemini API failed ({e}). Falling back to Groq...")
        groq_api_key = os.environ.get("GROQ_API_KEY")
        llm = ChatGroq(
            model="openai/gpt-oss-120b",
            api_key=groq_api_key,
            temperature=0,
            max_retries=3
        )
        llm_with_tools = llm.bind_tools([apply_code_transformation])
        response = llm_with_tools.invoke([system_prompt, user_prompt])
    
    identified_file = "unknown"
    
    # Execute the tool calls if the model made any
    if hasattr(response, "tool_calls") and response.tool_calls:
        for tool_call in response.tool_calls:
            if tool_call["name"] == "apply_code_transformation":
                args = tool_call["args"]
                file_path = args.get("file_path")
                old_snippet = args.get("old_code_snippet")
                new_snippet = args.get("new_code_snippet")
                
                if file_path:
                    # Resolve relative paths against the working directory
                    if not os.path.isabs(file_path):
                        file_path = os.path.normpath(os.path.join(work_dir, file_path))
                    
                    # --- Change 2: Reject file paths outside the repo ---
                    resolved_path = os.path.realpath(file_path)
                    resolved_work_dir = os.path.realpath(work_dir)
                    
                    if not resolved_path.startswith(resolved_work_dir + os.sep) and resolved_path != resolved_work_dir:
                        print(f"   🛡️  BLOCKED: Path traversal detected! "
                              f"'{file_path}' is outside the repository boundary.")
                        continue
                    
                    identified_file = file_path
                
                # Execute the tool
                try:
                    apply_code_transformation.invoke({
                        "file_path": file_path,
                        "old_code_snippet": old_snippet,
                        "new_code_snippet": new_snippet
                    })
                except Exception as e:
                    print(f"Error executing tool call: {e}")
    
    return {
        "retry_count": retry_count + 1,
        "current_file": identified_file
    }
