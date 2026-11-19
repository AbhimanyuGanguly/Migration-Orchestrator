from typing import TypedDict, List

class MigrationState(TypedDict):
    repo_path: str
    work_dir: str               # Temp copy or git branch — actual working directory
    language: str
    target_dependency: str
    target_version: str
    migration_rules: List[str]
    current_file: str
    test_stdout: str
    tests_passing: bool
    test_stderr: str
    previous_error: str         # Stores last cycle's error for duplicate detection
    repo_context: str
    retry_count: int
    max_retries: int            # Configurable via --max-retries CLI flag
