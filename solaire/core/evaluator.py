"""
Environment handling for the sys path and code execution.

This is necessary for running project code and managing runtime namespaces
of imported modules from user-generated code.
"""


import sys
from pathlib import Path
from typing import Any
from typing import Optional

from solaire.core import broker
from solaire.core import common_events
from solaire.core.broker import DUMMY_EVENT

_PROJECT_PATH: Optional[Path] = None
_USER_NAMESPACE: dict[str, Any] = {}
_INITIAL_MODULES: set[str] = set(sys.modules.keys())


def update_project_path(path: Path) -> None:
    """Update the project path and add it to sys.path.
    This will remove the previous project path, if it was valid.
    """
    global _PROJECT_PATH

    # Remove old project path if it exists
    if _PROJECT_PATH and _PROJECT_PATH.as_posix() in sys.path:
        sys.path.remove(_PROJECT_PATH.as_posix())

    if path.exists():
        _PROJECT_PATH = path
    else:
        raise ValueError(f'New project path does not exist {path}!')

    sys.path.insert(0, path.as_posix())


def _ensure_main_namespace(filename: Optional[Path] = None) -> None:
    """Ensure the persistent user namespace has __name__ == '__main__' and
    related dunders.
    """
    global _USER_NAMESPACE

    if '__name__' not in _USER_NAMESPACE:
        _USER_NAMESPACE['__name__'] = '__main__'

    _USER_NAMESPACE.setdefault('__package__', None)
    if filename is not None:
        _USER_NAMESPACE['__file__'] = filename.as_posix()


def reset_user_namespace() -> None:
    """Reset the persistent namespace to a clean module-like __main__ state."""
    global _USER_NAMESPACE
    _USER_NAMESPACE = {}
    _ensure_main_namespace()


def execute_user_code(
        code: str,
        *,
        filename: Optional[Path] = None,
        reset: bool = False
) -> Optional[str]:
    """Execute user code in a persistent namespace that maintains state
    between executions, similar to a Python REPL or Jupyter notebook.

    Args:
        code (str): The Python code to execute.
        filename (Optional[Path]): Pretend file path for better tracebacks and to
            populate __file__ in the user namespace.
        reset (bool): If True, reset the namespace before executing.
    Returns:
        Optional[str]: None if successful; otherwise an error message string.
    """
    common_events.show_output()

    global _USER_NAMESPACE

    try:
        if reset:
            reset_user_namespace()

        # Make sure __name__ == '__main__' and related dunders exist
        _ensure_main_namespace(filename=filename)

        # Compile with a filename for clearer tracebacks if provided
        code_obj = compile(
            code,
            filename.as_posix() if filename else '<user_code>',
            'exec'
        )

        # Execute code in the persistent user namespace
        exec(code_obj, _USER_NAMESPACE)
        return None
    except Exception as e:
        # Return the error message for display in the IDE
        error_type = type(e).__name__
        error_message = str(e)
        return f'{error_type}: {error_message}'
