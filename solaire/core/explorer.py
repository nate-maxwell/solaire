"""
PySide6 File Tree Widget for Code IDE.
A comprehensive file browser with icons, context menus, and file filtering.
"""


from pathlib import Path
from typing import Optional

from PySide6 import QtWidgets
from PySide6TK import QtWrappers


class SolaireFileTree(QtWidgets.QWidget):
    def __init__(self, parent: Optional[QtWidgets.QWidget]) -> None:
        super().__init__(parent)

        self._create_widgets()
        self._create_layout()
        self._create_connections()

    def _create_widgets(self) -> None:
        self.layout_main = QtWidgets.QVBoxLayout()

        self.lbl_header = QtWidgets.QLabel('Explorer')

        temp_path = Path(__file__).parent.parent.parent
        self.file_tree = QtWrappers.FileTreeWidget(temp_path, self)

    def _create_layout(self) -> None:
        self.setLayout(self.layout_main)
        self.layout_main.addWidget(self.lbl_header)
        self.layout_main.addWidget(self.file_tree)

    def _create_connections(self) -> None:
        ...
