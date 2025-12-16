"""
Primary project manager for editor.
Provides switching, loading, and saving data per project.
"""


from pathlib import Path
from typing import Optional

from PySide6 import QtWidgets
from PySide6TK import QtWrappers

from solaire.core import broker


class ProjectSelector(QtWidgets.QWidget):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

        self.project_combobox = QtWidgets.QComboBox()
        self.project_combobox.setFixedHeight(30)
        self.layout.addWidget(QtWidgets.QLabel('Project'))
        self.layout.addWidget(self.project_combobox)
        self.layout.addWidget(QtWrappers.HorizontalLine())

        broker.register_subscriber(
            'common_event',
            'open_folder',
            self._on_directory_changed
        )

    def _on_directory_changed(self, event: broker.Event) -> None:
        path = Path(event.data)
        if not path.is_dir():
            return

        self._add_unique_item(path.name)
        self.project_combobox.setCurrentText(path.name)

    def _add_unique_item(self, text: str) -> None:
        if self.project_combobox.findText(text) == -1:
            self.project_combobox.addItem(text)
