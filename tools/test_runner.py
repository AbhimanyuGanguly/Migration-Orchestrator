import subprocess
from langchain_core.tools import tool

@tool
def run_repo_tests(repo_path: str, language: str = "python") -> dict:
    """Run tests in the specified repository path based on language."""
    try:
        import os
        if language == "javascript":
            npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
            cmd = [npm_cmd, "test"]
        else:
            cmd = ["python", "-m", "pytest", "-W", "error"]
            
        result = subprocess.run(
            cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=60
        )
        return {
            "passed": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.TimeoutExpired as e:
        return {
            "passed": False,
            "stdout": e.stdout.decode('utf-8') if e.stdout else "",
            "stderr": f"Test execution timed out after 60 seconds. {e.stderr.decode('utf-8') if e.stderr else ''}"
        }
    except Exception as e:
        return {
            "passed": False,
            "stdout": "",
            "stderr": f"Error running tests: {str(e)}"
        }
