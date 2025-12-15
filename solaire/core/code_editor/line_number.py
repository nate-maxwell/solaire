"""
Gutter widget for holding line numbers in the code editor.
"""

from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets


class LineNumberArea(QtWidgets.QWidget):
    """
    A side-gutter widget responsible for rendering line numbers for a
    ``CodeEditor`` instance.

    Notes:
        - ``_LineNumberArea`` does not paint anything by itself; all
          drawing is delegated back to the parent editor.
        - ``sizeHint()`` returns a width based on the current block
          count so the gutter resizes correctly as line numbers grow
          into additional digits.
    """

    def __init__(self, code_editor: 'CodeEditor') -> None:
        super().__init__(code_editor)
        self.editor = code_editor

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(self.editor.line_number_area_width, 0)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        self.editor.line_number_area_paint_event(event)
