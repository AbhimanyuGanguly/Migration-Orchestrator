import ast
import os
import subprocess
import libcst as cst
from langchain_core.tools import tool

# --- Change 1: Test file patterns that the Surgeon must never touch ---
TEST_FILE_PATTERNS = (
    "test_", "tests_", "_test.", "_tests.",       # Python: test_foo.py, foo_test.py
    ".test.", ".tests.", ".spec.",                  # JS/TS: foo.test.js, foo.spec.ts
)

def _is_test_file(file_path: str) -> bool:
    """Check if a file is a test file based on its name."""
    basename = os.path.basename(file_path).lower()
    return any(pattern in basename for pattern in TEST_FILE_PATTERNS)


def _syntax_check(file_path: str) -> bool:
    """Validate syntax of a file after patching. Returns True if valid."""
    try:
        if file_path.endswith(".py"):
            # --- Change 3: Use ast.parse for Python syntax validation ---
            with open(file_path, "r", encoding="utf-8") as f:
                ast.parse(f.read())
            return True
        elif file_path.endswith((".js", ".jsx", ".ts", ".tsx")):
            # --- Change 3: Use node --check for JS syntax validation ---
            node_cmd = "node"
            result = subprocess.run(
                [node_cmd, "--check", file_path],
                capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0
        return True  # Unknown file type — skip check
    except Exception:
        return False


class SnippetTransformer(cst.CSTTransformer):
    def __init__(self, old_snippet: str, new_snippet: str):
        super().__init__()
        self.old_snippet = old_snippet
        self.new_snippet = new_snippet
        
        # Try to parse the snippets as statements or expressions
        try:
            self.old_statement = cst.parse_statement(old_snippet)
            self.new_statement = cst.parse_statement(new_snippet)
        except Exception:
            self.old_statement = None
            self.new_statement = None
            
        try:
            self.old_expression = cst.parse_expression(old_snippet)
            self.new_expression = cst.parse_expression(new_snippet)
        except Exception:
            self.old_expression = None
            self.new_expression = None

    def on_leave(self, original_node: cst.CSTNode, updated_node: cst.CSTNode) -> cst.CSTNode:
        # If we successfully parsed as a statement, check for a match
        if self.old_statement and isinstance(original_node, type(self.old_statement)):
            if original_node.deep_equals(self.old_statement):
                return self.new_statement
        
        # If we successfully parsed as an expression, check for a match
        if self.old_expression and isinstance(original_node, type(self.old_expression)):
            if original_node.deep_equals(self.old_expression):
                return self.new_expression
                
        return updated_node

@tool
def apply_code_transformation(file_path: str, old_code_snippet: str, new_code_snippet: str) -> bool:
    """Apply a code transformation to a file using abstract syntax trees to preserve formatting."""
    try:
        # --- Change 1: Block edits to test files ---
        if _is_test_file(file_path):
            print(f"   🛡️  BLOCKED: Refused to modify test file: {os.path.basename(file_path)}")
            return False
        
        with open(file_path, "r", encoding="utf-8") as f:
            source_code = f.read()

        # Skip CST parsing for JavaScript/TypeScript
        is_python = file_path.endswith('.py')
        modified_code = source_code
        
        if is_python:
            # Parse the source file into a Concrete Syntax Tree
            module = cst.parse_module(source_code)
            
            # Apply the transformation
            transformer = SnippetTransformer(old_code_snippet, new_code_snippet)
            modified_module = module.visit(transformer)
            
            # Write the modified CST back to the file
            modified_code = modified_module.code
        
        # Fallback to string replacement if strict CST matching failed or for non-Python files
        if modified_code == source_code:
            # --- Change 3: Require exactly one match in string-replace fallback ---
            match_count = source_code.count(old_code_snippet)
            if match_count == 0:
                return False  # old snippet not found in file
            if match_count > 1:
                print(f"   🛡️  BLOCKED: Old snippet found {match_count} times in {os.path.basename(file_path)}. "
                      f"Refusing ambiguous multi-replace. Require exactly 1 match.")
                return False
            modified_code = source_code.replace(old_code_snippet, new_code_snippet, 1)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(modified_code)
        
        # --- Change 3: Syntax-check after patch — undo if broken ---
        if not _syntax_check(file_path):
            print(f"   ⚠️  Syntax check FAILED after patching {os.path.basename(file_path)}. Undoing patch...")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(source_code)
            return False
            
        return True
    except Exception as e:
        print(f"Failed to transform code in {file_path}: {e}")
        return False
