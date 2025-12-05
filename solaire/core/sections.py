from PySide6 import QtGui
from PySide6 import QtWidgets

import solaire.media


class SectionsWidget(QtWidgets.QWidget):
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

        self.explorer_button = QtWidgets.QPushButton('')
        explorer_icon = QtGui.QIcon(solaire.media.ICON_FOLDER.as_posix())
        self.explorer_button.setIcon(explorer_icon)
        self.explorer_button.setToolTip('Explorer')

        self.plugin_button = QtWidgets.QPushButton('')
        plugin_icon = QtGui.QIcon(solaire.media.ICON_PLUGIN.as_posix())
        self.plugin_button.setIcon(plugin_icon)
        self.plugin_button.setToolTip('Plugins')

    def _create_layout(self) -> None:
        self.setLayout(self.layout)

        self.layout.addWidget(self.explorer_button)
        self.layout.addWidget(self.plugin_button)
        self.layout.addStretch()

    def _create_connections(self) -> None:
        ...
