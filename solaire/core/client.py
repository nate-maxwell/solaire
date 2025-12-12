"""
# Solaire Application Client

The primary application. This includes the Solaire main window, and primary
widget housing all window components.
"""


from typing import Optional

import PySide6TK.shapes
from PySide6 import QtCore
from PySide6 import QtWidgets
from PySide6TK import QtWrappers

import solaire.core.resources
from solaire.core import appdata
from solaire.core import broker
from solaire.core import explorer
from solaire.core import sections_bar
from solaire.core import shortucts
from solaire.core import status_bar
from solaire.core import editor_tabs
from solaire.core import toolbar
from solaire.core import output_tabs



splitter_style = """
QSplitter::handle {
    background: #444;
}
QSplitter::handle:hover {
    background: #777;
}
"""


class SolaireClientWidget(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)

        self._create_widgets()
        self._create_layout()

    def _create_widgets(self) -> None:
        self.layout = QtWidgets.QHBoxLayout()
        self.sections_bar = sections_bar.SectionsBar(self)
        self.tab_editor = editor_tabs.EditorTabWidget(self)
        self.tab_outputs = output_tabs.OutputTabWidget(self)

        self.splitter_bottom = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        self.splitter_bottom.setStyleSheet(splitter_style)
        self.splitter_left = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self.splitter_left.setStyleSheet(splitter_style)

        self.explorer_widget = QtWidgets.QWidget()
        self.vlayout_explorers = QtWidgets.QVBoxLayout()
        self.vlayout_explorers.setContentsMargins(0, 0, 0, 0)
        self.file_explorer = explorer.ExplorerWidget(self)

    def _create_layout(self) -> None:
        self.explorer_widget.setLayout(self.vlayout_explorers)
        self.vlayout_explorers.addWidget(self.file_explorer)
        self.vlayout_explorers.addWidget(self.explorer_widget)

        self.splitter_bottom.addWidget(self.tab_editor)
        self.splitter_bottom.addWidget(self.tab_outputs)
        self.splitter_bottom.setSizes([(1080 - 200), 200])

        self.splitter_left.addWidget(self.explorer_widget)
        self.splitter_left.addWidget(self.splitter_bottom)
        self.splitter_left.setSizes([(1920 - 1700), 1700])

        self.setLayout(self.layout)
        self.layout.addWidget(self.sections_bar)
        self.layout.addWidget(PySide6TK.shapes.VerticalLine())
        self.layout.addWidget(self.splitter_left)


class SolaireClientWindow(QtWrappers.MainWindow):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(
            window_name='Solaire',
            parent=parent,
            icon_path=solaire.core.resources.ICON_PATH
        )
        appdata.initialize()

        QtWrappers.set_style(self, QtWrappers.QSS_COMBINEAR)
        shortucts.init_shortcut_manager(self)  # must come before main widget
        broker.register_source('SYSTEM')

        self._is_fullscreen = False
        broker.register_subscriber(
            'window',
            'toggle_full_screen',
            self.toggle_fullscreen
        )

        self.widget_main = SolaireClientWidget()
        self.setCentralWidget(self.widget_main)

        self.toolbar = toolbar.SolaireToolbar(self)
        self.addToolBar(QtCore.Qt.ToolBarArea.TopToolBarArea, self.toolbar)
        self.status_bar = status_bar.StatusBar(self)
        self.addToolBar(QtCore.Qt.ToolBarArea.BottomToolBarArea, self.status_bar)

    def toggle_fullscreen(self, _: broker.Event) -> None:
        if not self._is_fullscreen:
            self.showFullScreen()
        else:
            self.showNormal()

        self._is_fullscreen = not self._is_fullscreen
