"""
PySide6 File Tree Widget for Code IDE.
A comprehensive file browser with icons, context menus, and file filtering.
"""


from pathlib import Path
from typing import Optional

from PySide6 import QtWidgets
from PySide6TK import QtWrappers

from solaire.core import broker
from solaire.core import common_events


class SolaireFileTree(QtWidgets.QWidget):
    def __init__(self, parent: Optional[QtWidgets.QWidget]) -> None:
        super().__init__(parent)
        broker.register_source('solaire_file_tree')

        self._create_widgets()
        self._create_layout()
        self._create_connections()
        self._create_subscriptions()

    def _create_widgets(self) -> None:
        self.layout_main = QtWidgets.QVBoxLayout()
        self.layout_main.setContentsMargins(0, 0, 0, 0)

        self.lbl_header = QtWidgets.QLabel('Explorer')

        temp_path = Path(__file__).parent.parent.parent
        self.file_tree = QtWrappers.FileTreeWidget(temp_path, self)
        common_events.directory_changed(temp_path)

    def _create_layout(self) -> None:
        self.setLayout(self.layout_main)
        self.layout_main.addWidget(self.lbl_header)
        self.layout_main.addWidget(self.file_tree)

    def _create_connections(self) -> None:
        self.file_tree.file_opened.connect(lambda path: file_opened(path))
        self.file_tree.file_selected.connect(lambda path: file_selected(path))

    def _create_subscriptions(self) -> None:
        broker.register_subscriber(
            'common_event',
            'open_folder',
            self._on_directory_changed
        )

    def _on_directory_changed(self, event: broker.Event) -> None:
        self.file_tree.set_root_path(event.data)


def file_opened(path: str) -> None:
    event = broker.Event('solaire_file_tree', 'file_opened', Path(path))
    broker.emit(event)


def file_selected(path: str) -> None:
    event = broker.Event('solaire_file_tree', 'file_selected', Path(path))
    broker.emit(event)
