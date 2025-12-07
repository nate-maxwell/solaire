from PySide6 import QtGui
from PySide6 import QtWidgets

import solaire.core.resources
from solaire.core import broker


class SectionsBar(QtWidgets.QWidget):
    """Vertical bar with buttons for the file explorer, plugins manager, and
    git menus.
    """
    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)

        self._create_widgets()
        self._create_layout()
        self._create_connections()

    def _create_widgets(self) -> None:
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.btn_explorer = QtWidgets.QPushButton('')
        explorer_icon = QtGui.QIcon(solaire.core.resources.ICON_FOLDER.as_posix())
        self.btn_explorer.setIcon(explorer_icon)
        self.btn_explorer.setToolTip('Explorer')

        self.btn_plugin = QtWidgets.QPushButton('')
        plugin_icon = QtGui.QIcon(solaire.core.resources.ICON_PLUGIN.as_posix())
        self.btn_plugin.setIcon(plugin_icon)
        self.btn_plugin.setToolTip('Plugins')

        self.btn_structure = QtWidgets.QPushButton('')
        structure_icon = QtGui.QIcon(solaire.core.resources.ICON_STRUCTURE.as_posix())
        self.btn_structure.setIcon(structure_icon)
        self.btn_structure.setToolTip('Code Structure')

    def _create_layout(self) -> None:
        self.setLayout(self.layout)

        self.layout.addWidget(self.btn_explorer)
        self.layout.addWidget(self.btn_plugin)
        self.layout.addWidget(self.btn_structure)
        self.layout.addStretch()

    def _create_connections(self) -> None:
        self.btn_explorer.clicked.connect(toggle_explorer)
        self.btn_structure.clicked.connect(toggle_structure)


def toggle_explorer() -> None:
    """Signal to toggle visibility on file explorer."""
    event = broker.Event('sections_bar', 'toggle_explorer')
    broker.emit(event)


def toggle_structure() -> None:
    """Signal to toggle visibility on structure explorer."""
    event = broker.Event('sections_bar', 'toggle_structure')
    broker.emit(event)
