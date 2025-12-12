from pathlib import Path
from typing import Optional
from typing import Type
from typing import TypeVar

from PySide6 import QtGui
from PySide6TK import QtWrappers

T_Highlighter = TypeVar('T_Highlighter', bound=QtGui.QSyntaxHighlighter)

SyntaxHighlighter = Type[T_Highlighter]
"""Any QSyntaxHighlighter class object or derived class object."""


def generate_highlighter_from_file(filepath: Path) -> Optional[SyntaxHighlighter]:
    """Returns the corresponding highlighter from the file suffix."""
    suffix_highlighters = {
        '.py': QtWrappers.PythonHighlighter,
        '.pyw': QtWrappers.PythonHighlighter,
        '.json': QtWrappers.JsonHighlighter,
    }

    if filepath.suffix in suffix_highlighters:
        return suffix_highlighters[filepath.suffix]
    return None
