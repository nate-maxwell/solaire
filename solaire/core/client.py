"""
# Solaire Application Client

The primary application. This includes the Solaire main window, and primary
widget housing all window components.
"""


import PySide6TK.shapes
from PySide6 import QtCore
from PySide6 import QtWidgets
from PySide6TK import QtWrappers

import solaire.core.resources
from solaire.core import broker
from solaire.core import explorer
from solaire.core import sections_bar
from solaire.core import shortucts
from solaire.core import status_bar
from solaire.core import tabs
from solaire.core import toolbar


class SolaireClientWidget(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)

        self._create_widgets()
        self._create_layout()

    def _create_widgets(self) -> None:
        self.layout = QtWidgets.QHBoxLayout()
        self.sections_bar = sections_bar.SectionsBar(self)
        self.tab_manager = tabs.EditorTabWidget(self)
        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)

        self.explorer_widget = QtWidgets.QWidget()
        self.vlayout_explorers = QtWidgets.QVBoxLayout()
        self.vlayout_explorers.setContentsMargins(0, 0, 0, 0)
        self.file_explorer = explorer.ExplorerWidget(self)

    def _create_layout(self) -> None:
        self.explorer_widget.setLayout(self.vlayout_explorers)
        self.vlayout_explorers.addWidget(self.file_explorer)
        self.vlayout_explorers.addWidget(self.explorer_widget)

        self.splitter.addWidget(self.explorer_widget)
        self.splitter.addWidget(self.tab_manager)
        self.splitter.setSizes([(1920 - 1700), 1700])

        self.setLayout(self.layout)
        self.layout.addWidget(self.sections_bar)
        self.layout.addWidget(PySide6TK.shapes.VerticalLine())
        self.layout.addWidget(self.splitter)


class SolaireClientWindow(QtWrappers.MainWindow):
    def __init__(self) -> None:
        super().__init__('Solaire', icon_path=solaire.core.resources.ICON_PATH)
        QtWrappers.set_style(self, QtWrappers.QSS_COMBINEAR)
        shortucts.init_shortcut_manager(self)  # must come before main widget
        broker.register_source('SYSTEM')

        self.widget_main = SolaireClientWidget()
        self.setCentralWidget(self.widget_main)

        self.toolbar = toolbar.SolaireToolbar(self)
        self.addToolBar(QtCore.Qt.ToolBarArea.TopToolBarArea, self.toolbar)
        self.status_bar = status_bar.StatusBar(self)
        self.addToolBar(QtCore.Qt.ToolBarArea.BottomToolBarArea, self.status_bar)
