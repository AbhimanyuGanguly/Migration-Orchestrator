import argparse
import os
import sys
import shutil
import tempfile
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
from workflows.graph import graph

def main():
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Multi-provider LangGraph Dependency Orchestrator")
    parser.add_argument("--repo", type=str, required=True, help="Path to the repository to migrate")
    parser.add_argument("--dependency", type=str, required=True, help="Target dependency name")
    parser.add_argument("--version", type=str, required=True, help="Target version to migrate to")
    parser.add_argument("--max-retries", type=int, default=5, help="Maximum retry attempts for the Surgeon (default: 5)")
    
    args = parser.parse_args()
    
    repo_path = os.path.abspath(args.repo)
    
    language = "python"
    if os.path.exists(os.path.join(repo_path, "package.json")):
        language = "javascript"
    
    # --- Change 4: Create a temporary working copy for rollback safety ---
    work_dir = tempfile.mkdtemp(prefix="migration_")
    print(f"\n📋 Creating temporary working copy at: {work_dir}")
    
    # Copy the repo into the temp directory
    temp_repo = os.path.join(work_dir, os.path.basename(repo_path))
    shutil.copytree(repo_path, temp_repo)
    print(f"   ✅ Working copy ready: {temp_repo}")
    
    initial_state = {
        "repo_path": repo_path,
        "work_dir": temp_repo,
        "language": language,
        "target_dependency": args.dependency,
        "target_version": args.version,
        "retry_count": 0,
        "max_retries": args.max_retries,
        "migration_rules": [],
        "current_file": "",
        "test_stdout": "",
        "test_stderr": "",
        "previous_error": "",
        "tests_passing": False,
        "repo_context": ""
    }
    
    print(f"\n🚀 Starting Migration Orchestrator for {args.dependency} -> v{args.version}\n")
    print(f"📂 Repository: {repo_path} ({language.capitalize()})")
    print(f"🔁 Max retries: {args.max_retries}")
    print("-" * 60)
    
    migration_succeeded = False
    
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
                    if passed:
                        migration_succeeded = True
                    if not passed:
                        # Print last few lines of stderr for context
                        stderr = state_update.get("test_stderr", "")
                        lines = stderr.strip().split("\n") if stderr else []
                        print(f"   ⚠️  Error output snippet: {lines[-1] if lines else 'None'}")
                
                elif node == "surgeon_node":
                    file_modified = state_update.get("current_file", "unknown")
                    retry = state_update.get("retry_count", 0)
                    max_r = args.max_retries
                    print(f"   🛠️  Surgeon operated on file: {file_modified} (Attempt {retry}/{max_r})")
                    
            print("-" * 60)
        
        # --- Change 4: Rollback or apply based on outcome ---
        if migration_succeeded:
            print("\n✅ Migration succeeded! Applying changes to original repository...")
            # Copy modified files back from temp to original repo
            for root, dirs, files in os.walk(temp_repo):
                for file in files:
                    src = os.path.join(root, file)
                    rel_path = os.path.relpath(src, temp_repo)
                    dst = os.path.join(repo_path, rel_path)
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy2(src, dst)
            print("   📁 Changes applied successfully.")
        else:
            print("\n🔙 Migration failed after all retries. Discarding working copy.")
            print("   📁 Original repository is UNTOUCHED.")
        
        print("\n🎉 Orchestrator execution completed!\n")
        
    except Exception as e:
        print(f"\n🚨 Critical error during execution: {e}")
        print("🔙 Discarding working copy. Original repository is UNTOUCHED.\n")
    finally:
        # Always clean up the temp directory
        shutil.rmtree(work_dir, ignore_errors=True)
        print(f"🧹 Cleaned up temporary directory: {work_dir}")

if __name__ == "__main__":
    main()
