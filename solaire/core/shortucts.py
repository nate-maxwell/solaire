from typing import Optional

from PySide6 import QtWidgets
from PySide6TK import QtWrappers


class ShortcutManager(QtWrappers.KeyShortcutManager):
    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)


shortcut_manager: Optional[ShortcutManager] = None


def init_shortcut_manager(parent: QtWidgets.QWidget) -> ShortcutManager:
    global shortcut_manager
    if shortcut_manager is None:
        shortcut_manager = ShortcutManager(parent)

    return shortcut_manager
