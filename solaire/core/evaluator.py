"""
Environment handling for the sys path and code execution.

This is necessary for running project code and managing runtime namespaces
of imported modules from user-generated code.
"""


import sys
from pathlib import Path
from typing import Any
from typing import Optional


_PROJECT_PATH: Optional[Path] = None
_USER_NAMESPACE: dict[str, Any] = {}
_INITIAL_MODULES: set[str] = set(sys.modules.keys())


def update_project_path(path: Path) -> None:
    """Update the project path and add it to sys.path."""
    global _PROJECT_PATH

    # Remove old project path if it exists
    if _PROJECT_PATH and _PROJECT_PATH.as_posix() in sys.path:
        sys.path.remove(_PROJECT_PATH.as_posix())

    if path.exists():
        _PROJECT_PATH = path
    else:
        raise ValueError(f'New project path does not exist {path}!')

    sys.path.insert(0, path.as_posix())
