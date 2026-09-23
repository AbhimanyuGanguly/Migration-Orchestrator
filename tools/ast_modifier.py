import libcst as cst
from langchain_core.tools import tool

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
            if old_code_snippet in source_code:
                modified_code = source_code.replace(old_code_snippet, new_code_snippet)
            else:
                return False # old snippet not found in file

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(modified_code)
            
        return True
    except Exception as e:
        print(f"Failed to transform code in {file_path}: {e}")
        return False
