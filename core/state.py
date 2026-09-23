from typing import TypedDict, List

class MigrationState(TypedDict):
    repo_path: str
    language: str
    target_dependency: str
    target_version: str
    migration_rules: List[str]
    current_file: str
    test_stdout: str
    tests_passing: bool
    test_stderr: str
    repo_context: str
    retry_count: int
