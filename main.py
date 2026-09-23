import argparse
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
from workflows.graph import graph

def main():
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Multi-provider LangGraph Dependency Orchestrator")
    parser.add_argument("--repo", type=str, required=True, help="Path to the repository to migrate")
    parser.add_argument("--dependency", type=str, required=True, help="Target dependency name")
    parser.add_argument("--version", type=str, required=True, help="Target version to migrate to")
    
    args = parser.parse_args()
    
    language = "python"
    if os.path.exists(os.path.join(args.repo, "package.json")):
        language = "javascript"
    
    initial_state = {
        "repo_path": args.repo,
        "language": language,
        "target_dependency": args.dependency,
        "target_version": args.version,
        "retry_count": 0,
        "migration_rules": [],
        "current_file": "",
        "test_stdout": "",
        "test_stderr": "",
        "tests_passing": False,
        "repo_context": ""
    }
    
    print(f"\n🚀 Starting Migration Orchestrator for {args.dependency} -> v{args.version}\n")
    print(f"📂 Repository: {args.repo} ({language.capitalize()})")
    print("-" * 60)
    
    try:
        # Stream events beautifully to the console
        for event in graph.stream(initial_state):
            for node, state_update in event.items():
                print(f"\n🔄 [NODE EXECUTION]: {node}")
                
                if node == "researcher_node":
                    rules = state_update.get("migration_rules", [])
                    print(f"   🔍 Found {len(rules)} migration rules.")
                
                elif node == "validator_node":
                    passed = state_update.get("tests_passing", False)
                    status = "✅ PASSED" if passed else "❌ FAILED"
                    print(f"   🧪 Tests {status}")
                    if not passed:
                        # Print last few lines of stderr for context
                        stderr = state_update.get("test_stderr", "")
                        lines = stderr.strip().split("\n") if stderr else []
                        print(f"   ⚠️  Error output snippet: {lines[-1] if lines else 'None'}")
                
                elif node == "surgeon_node":
                    file_modified = state_update.get("current_file", "unknown")
                    retry = state_update.get("retry_count", 0)
                    print(f"   🛠️  Surgeon operated on file: {file_modified} (Attempt {retry}/5)")
                    
            print("-" * 60)
            
        print("\n🎉 Orchestrator execution completed!\n")
        
    except Exception as e:
        print(f"\n🚨 Critical error during execution: {e}\n")

if __name__ == "__main__":
    main()
