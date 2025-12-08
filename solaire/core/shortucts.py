"""
Shortcut management for the Solaire applications.
"""


from typing import Optional

from PySide6 import QtWidgets
from PySide6TK import QtWrappers

from solaire.core import common_events


class ShortcutManager(QtWrappers.KeyShortcutManager):
    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)

        self._create_shortcuts()

    def _create_shortcuts(self) -> None:
        self.add_shortcut(
            'save_file',
            'Ctrl+S',
            common_events.save_file,
            'Save the current file.'
        )
        self.add_shortcut(
            'save_all',
            'Ctrl+Shift+S',
            common_events.save_all,
            'Save all current files.'
        )
        self.add_shortcut(
            'open_file',
            'Ctrl+O',
            common_events.open_file,
            'Open a file.'
        )
        self.add_shortcut(
            'open_folder',
            'Ctrl+Shift+O',
            common_events.open_folder,
            'Open a file.'
        )
        self.add_shortcut(
            'run_code',
            'Ctrl+Return',
            common_events.run_code,
            'Run active tab code.'
        )
        self.add_shortcut(
            'run_code_alt',
            'Ctrl+Enter',
            common_events.run_code,
            'Run active tab code.'
        )
        self.add_shortcut(
            'open_terminal',
            'Ctrl+`',
            common_events.show_terminal,
            'Show the terminal.'
        )


shortcut_manager: Optional[ShortcutManager] = None


def init_shortcut_manager(parent: QtWidgets.QWidget) -> ShortcutManager:
    global shortcut_manager
    if shortcut_manager is None:
        shortcut_manager = ShortcutManager(parent)

    return shortcut_manager
