from PySide6 import QtWidgets

from solaire.core import code_text_edit
from solaire.core import minimap


class CodeEditor(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)
        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.code_text_edit = code_text_edit.CodeTextEdit()
        self.minimap = minimap.CodeMiniMap(self.code_text_edit, self)

        self.layout.addWidget(self.code_text_edit)
        self.layout.addWidget(self.minimap)
