"""
# Solaire Application Client

* Description:

    The primary application. This includes the Solaire main window, and primary
    widget housing all window components.
"""


from PySide6 import QtCore
from PySide6 import QtWidgets
from PySide6TK import QtWrappers

import solaire.core.resources
from solaire.core import tabs
from solaire.core import toolbar
from solaire.core import status_bar
from solaire.core import explorer
from solaire.core import sections_bar
from solaire.core import shortucts

from solaire.core import broker


class SolaireClientWidget(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)

        self._create_widgets()
        self._create_layout()
        self._create_subscriptions()

    def _create_widgets(self) -> None:
        self.layout = QtWidgets.QHBoxLayout()
        self.sections = sections_bar.SectionsBar(self)
        self.tab_manager = tabs.EditorTabWidget(self)
        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self.file_explorer = explorer.SolaireFileTree(parent=self)

    def _create_layout(self) -> None:
        self.setLayout(self.layout)

        self.splitter.addWidget(self.file_explorer)
        self.splitter.addWidget(self.tab_manager)
        self.splitter.setSizes([(1920 - 1700), 1700])

        self.layout.addWidget(self.sections)
        self.layout.addWidget(self.splitter)

    def _create_subscriptions(self) -> None:
        broker.register_subscriber(
            'sections_bar',
            'toggle_explorer',
            self.toggle_explorer_visibility
        )

    def toggle_explorer_visibility(self, _: broker.Event) -> None:
        self.file_explorer.setVisible(not self.file_explorer.isVisible())


class SolaireClientWindow(QtWrappers.MainWindow):
    def __init__(self) -> None:
        super().__init__('Solaire', icon_path=solaire.core.resources.ICON_PATH)
        QtWrappers.set_style(self, QtWrappers.QSS_DIFFNES)
        shortucts.init_shortcut_manager(self)  # must come before main widget

        self.widget_main = SolaireClientWidget()
        self.setCentralWidget(self.widget_main)

        self.toolbar = toolbar.SolaireToolbar(self)
        self.addToolBar(QtCore.Qt.ToolBarArea.TopToolBarArea, self.toolbar)
        self.status_bar = status_bar.StatusBar(self)
        self.addToolBar(QtCore.Qt.ToolBarArea.BottomToolBarArea, self.status_bar)
