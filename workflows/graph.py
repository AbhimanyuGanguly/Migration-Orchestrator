import os
import fnmatch
from langgraph.graph import StateGraph, START, END
from core.state import MigrationState
from agents.researcher import research_migration
from agents.surgeon import modify_codebase
from tools.test_runner import run_repo_tests

# --- Change 6: Patterns to always exclude from repo_context ---
ALWAYS_EXCLUDE = {
    ".env", ".env.local", ".env.production", ".env.staging",
    ".env.development", ".env.test",
    "id_rsa", "id_ed25519", "*.pem", "*.key", "*.cert",
    "*.secret", "credentials.json", "service-account.json",
    "package-lock.json", "yarn.lock",
}

def _load_gitignore_patterns(repo_path: str) -> list:
    """Parse .gitignore and return a list of glob patterns."""
    gitignore_path = os.path.join(repo_path, ".gitignore")
    patterns = []
    if os.path.exists(gitignore_path):
        try:
            with open(gitignore_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        patterns.append(line)
        except Exception:
            pass
    return patterns

def _is_excluded(file_path: str, rel_path: str, gitignore_patterns: list) -> bool:
    """Check if a file should be excluded from repo_context."""
    basename = os.path.basename(file_path)
    
    # Check against always-exclude set
    for pattern in ALWAYS_EXCLUDE:
        if fnmatch.fnmatch(basename, pattern):
            return True
    
    # Check against .gitignore patterns
    for pattern in gitignore_patterns:
        # Match against both the basename and the relative path
        if fnmatch.fnmatch(basename, pattern) or fnmatch.fnmatch(rel_path, pattern):
            return True
        # Handle directory patterns like "node_modules/"
        if pattern.endswith("/") and pattern.rstrip("/") in rel_path.split(os.sep):
            return True
    
    return False


def researcher_node(state: MigrationState) -> dict:
    return research_migration(state)

def validator_node(state: MigrationState) -> dict:
    # Use work_dir (temp copy) for all operations
    work_dir = state.get("work_dir", state.get("repo_path"))
    language = state.get("language", "python")
    test_results = run_repo_tests.invoke({"repo_path": work_dir, "language": language})
    
    combined = (test_results.get("stdout") or "") + "\n" + (test_results.get("stderr") or "")
    error_output = combined[-4000:] if combined.strip() else "None"
    
    print(f"   ⚠️  Error output snippet: {error_output[:100].strip()}...")
    
    # --- Change 6: Exclude .env, key files, and .gitignore entries from repo_context ---
    gitignore_patterns = _load_gitignore_patterns(work_dir)
    
    repo_context = ""
    valid_extensions = (".py",) if language == "python" else (".js", ".jsx", ".ts", ".tsx")
    
    for root, dirs, files in os.walk(work_dir):
        # Skip node_modules to avoid scanning thousands of files
        if "node_modules" in dirs:
            dirs.remove("node_modules")
        # Skip hidden directories like .git
        dirs[:] = [d for d in dirs if not d.startswith(".")]
            
        for file in files:
            if file.endswith(valid_extensions):
                path = os.path.join(root, file)
                rel_path = os.path.relpath(path, work_dir)
                
                # Check exclusion rules
                if _is_excluded(path, rel_path, gitignore_patterns):
                    continue
                
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        repo_context += f"\n--- File: {rel_path} ---\n{f.read()}\n"
                except Exception:
                    pass
    
    # --- Change 5: Store current error for duplicate detection ---
    current_error = error_output.strip() if error_output else ""
    
    return {
        "tests_passing": test_results["passed"],
        "test_stderr": error_output,
        "previous_error": state.get("test_stderr", ""),  # Save last cycle's error
        "repo_context": repo_context
    }

def surgeon_node(state: MigrationState) -> dict:
    return modify_codebase(state)

def should_continue(state: MigrationState) -> str:
    tests_passing = state.get("tests_passing", False)
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 5)
    
    # Success — exit loop
    if tests_passing:
        return "end"
    
    # --- Change 5: Stop early if the same error appears twice ---
    current_error = state.get("test_stderr", "").strip()
    previous_error = state.get("previous_error", "").strip()
    if current_error and previous_error and current_error == previous_error:
        print("   🔁 EARLY STOP: Same error appeared twice in a row. The model is stuck.")
        return "end"
    
    # Budget check using configurable max_retries
    if retry_count < max_retries:
        return "continue"
    
    return "end"

# Initialize graph
workflow = StateGraph(MigrationState)

# Define nodes
workflow.add_node("researcher_node", researcher_node)
workflow.add_node("validator_node", validator_node)
workflow.add_node("surgeon_node", surgeon_node)

# Define flow
workflow.add_edge(START, "researcher_node")
workflow.add_edge("researcher_node", "validator_node")

workflow.add_conditional_edges(
    "validator_node",
    should_continue,
    {
        "continue": "surgeon_node",
        "end": END
    }
)

workflow.add_edge("surgeon_node", "validator_node")

graph = workflow.compile()
