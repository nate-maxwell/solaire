from dataclasses import dataclass

from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets


@dataclass
class FoldRegion:
    """Represents a foldable region in the document."""
    start_block: int
    end_block: int
    is_folded: bool = False


class FoldArea(QtWidgets.QWidget):
    """Widget for displaying fold indicators."""

    def __init__(self, code_editor: 'CodeEditor') -> None:
        super().__init__(code_editor)
        self.editor = code_editor
        self.setMouseTracking(True)
        self._hover_block = -1

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(16, 0)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        self.editor.fold_area_paint_event(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        block_number = self.editor.get_block_number_at_pos(event.pos().y())
        if block_number != self._hover_block:
            self._hover_block = block_number
            self.update()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            block_number = self.editor.get_block_number_at_pos(event.pos().y())
            self.editor.toggle_fold(block_number)
