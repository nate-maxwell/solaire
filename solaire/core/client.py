
from PySide6 import QtCore
from PySide6 import QtWidgets
from PySide6TK import QtWrappers

import solaire.media
from solaire.core import tabs
from solaire.core import toolbar
from solaire.core import status_bar
from solaire.core import explorer
from solaire.core import sections
from solaire.core import shortucts


class SolaireClientWidget(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)

        self._create_widgets()
        self._create_layout()
        self._create_connections()

    def _create_widgets(self) -> None:
        self.layout = QtWidgets.QHBoxLayout()
        self.sections = sections.SectionsWidget(self)
        self.tab_manager = tabs.SolaireTabManager(self)
        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self.file_explorer = explorer.FileExplorer(self)

    def _create_layout(self) -> None:
        self.setLayout(self.layout)

        self.splitter.addWidget(self.tab_manager)
        self.splitter.addWidget(self.file_explorer)
        self.splitter.setSizes([1700, (1920 - 1700 - 40)])

        self.layout.addWidget(self.sections)
        self.layout.addWidget(self.splitter)

    def _create_connections(self) -> None:
        ...


class SolaireClientWindow(QtWrappers.MainWindow):
    def __init__(self) -> None:
        super().__init__('Solaire', icon_path=solaire.media.ICON_PATH)
        QtWrappers.set_style(self, QtWrappers.QSS_DIFFNES)
        shortucts.init_shortcut_manager(self)  # must come before main widget

        self.widget_main = SolaireClientWidget()
        self.setCentralWidget(self.widget_main)

        self.toolbar = toolbar.SolaireToolbar(self)
        self.addToolBar(QtCore.Qt.ToolBarArea.TopToolBarArea, self.toolbar)
        self.status_bar = status_bar.StatusBar(self)
        self.addToolBar(QtCore.Qt.ToolBarArea.BottomToolBarArea, self.status_bar)
