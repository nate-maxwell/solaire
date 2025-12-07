from pathlib import Path
from typing import Optional

from PySide6 import QtWidgets
from PySide6TK import QtWrappers

from solaire.core import broker


class ShortcutManager(QtWrappers.KeyShortcutManager):
    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)
        broker.register_source('shortcut_manager')

        self._create_shortcuts()

    def _create_shortcuts(self) -> None:
        self.add_shortcut(
            'save_file',
            'Ctrl+S',
            save_file,
            'Save the current file.'
        )
        self.add_shortcut(
            'save_all',
            'Ctrl+Shift+S',
            save_all,
            'Save all current files.'
        )
        self.add_shortcut(
            'open_file',
            'Ctrl+O',
            open_file,
            'Open a file.'
        )


def save_file() -> None:
    event = broker.Event(
        'shortcut_manager',
        'save_file'
    )
    broker.emit(event)


def save_all() -> None:
    event = broker.Event(
        'shortcut_manager',
        'save_all'
    )
    broker.emit(event)


def open_file() -> None:
    file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
        None,
        'Select a File',
        '',
        'All Files (*);;Python Files (*.py);;Text Files (*.txt)'
    )

    if not file_path:
        return

    event = broker.Event(
        'shortcut_manager',
        'open_file',
        Path(file_path)
    )
    broker.emit(event)


shortcut_manager: Optional[ShortcutManager] = None


def init_shortcut_manager(parent: QtWidgets.QWidget) -> ShortcutManager:
    global shortcut_manager
    if shortcut_manager is None:
        shortcut_manager = ShortcutManager(parent)

    return shortcut_manager
