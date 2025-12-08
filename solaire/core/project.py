"""
Project root path and sys path handling.

This is necessary for running project code and managing runtime namespaces.
"""


import sys
from pathlib import Path
from typing import Optional


_PROJECT_PATH: Optional[Path] = None


def update_project_path(path: Path) -> None:
    global _PROJECT_PATH

    if path.exists():
        _PROJECT_PATH = path
    else:
        raise ValueError(f'New project path does not exist {path}!')
