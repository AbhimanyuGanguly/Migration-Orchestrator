from langgraph.graph import StateGraph, START, END
from core.state import MigrationState
from agents.researcher import research_migration
from agents.surgeon import modify_codebase
from tools.test_runner import run_repo_tests

def researcher_node(state: MigrationState) -> dict:
    return research_migration(state)

def validator_node(state: MigrationState) -> dict:
    repo_path = state.get("repo_path")
    language = state.get("language", "python")
    test_results = run_repo_tests.invoke({"repo_path": repo_path, "language": language})
    
    combined = (test_results.get("stdout") or "") + "\n" + (test_results.get("stderr") or "")
    error_output = combined[-4000:] if combined.strip() else "None"
    
    print(f"   ⚠️  Error output snippet: {error_output[:100].strip()}...")
    
    import os
    repo_context = ""
    valid_extensions = (".py",) if language == "python" else (".js", ".jsx", ".ts", ".tsx")
    
    for root, dirs, files in os.walk(repo_path):
        # Skip node_modules to avoid scanning thousands of files
        if "node_modules" in dirs:
            dirs.remove("node_modules")
            
        for file in files:
            if file.endswith(valid_extensions):
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        repo_context += f"\n--- File: {file} ---\n{f.read()}\n"
                except Exception:
                    pass
    
    return {
        "tests_passing": test_results["passed"],
        "test_stderr": error_output,
        "repo_context": repo_context
    }

def surgeon_node(state: MigrationState) -> dict:
    return modify_codebase(state)

def should_continue(state: MigrationState) -> str:
    tests_passing = state.get("tests_passing", False)
    retry_count = state.get("retry_count", 0)
    
    if tests_passing:
        return "end"
    if not tests_passing and retry_count < 5:
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
