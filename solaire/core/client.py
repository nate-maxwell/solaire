"""
# Solaire Application Client

The primary application. This includes the Solaire main window, and primary
widget housing all window components.

Doubles as the primary startup process for the editor. The client main window
loads and initializes all systems and then constructs all widgets that get
placed on screen.
"""


from pathlib import Path
from typing import Optional

import PySide6TK.shapes
from PySide6 import QtCore
from PySide6 import QtWidgets
from PySide6TK import QtWrappers

import solaire.core.resources
from solaire.core import appdata
from solaire.core import broker
from solaire.core import sidebar
from solaire.core import sections_bar
from solaire.core import shortucts
from solaire.core import status_bar
from solaire.core import editor_tabs
from solaire.core import toolbar
from solaire.core import output_tabs
from solaire.core import theme



splitter_style = """
QSplitter::handle {
    background: #444;
}
QSplitter::handle:hover {
    background: #777;
}
"""


class SolaireClientWidget(QtWidgets.QWidget):
    """
    The primary widget, and component widgets, within the client.

    The client widget, and child component widgets, assume all editor systems
    have been loaded and initialized.
    """

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

        self.file_explorer = sidebar.SideBar(self)

    def _create_layout(self) -> None:
        self.splitter_bottom.addWidget(self.tab_editor)
        self.splitter_bottom.addWidget(self.tab_outputs)
        self.splitter_bottom.setSizes([(1080 - 200), 200])

        self.splitter_left.addWidget(self.file_explorer)
        self.splitter_left.addWidget(self.splitter_bottom)
        self.splitter_left.setSizes([(1920 - 1700), 1700])

        self.setLayout(self.layout)
        self.layout.addWidget(self.sections_bar)
        self.layout.addWidget(PySide6TK.shapes.VerticalLine())
        self.layout.addWidget(self.splitter_left)


class SolaireClientWindow(QtWrappers.MainWindow):
    """
    Primarily responsible for initializing all system logic before assembling
    the toolbar, primary widget, and status bar (also a toolbar).

    Primary systems initialization must come before component widget
    construction as many of the component widgets utilize aforementioned
    systems.
    """

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(
            window_name='Solaire',
            parent=parent,
            icon_path=solaire.core.resources.ICON_PATH
        )

        # -----Primary Systems Initialization-----
        shortucts.init_shortcut_manager(self)
        broker.register_source('SYSTEM')
        appdata.initialize()
        self._register_subscribers()
        self._is_fullscreen = False

        # -----Window Layout-----
        self.toolbar = toolbar.SolaireToolbar(self)
        self.addToolBar(QtCore.Qt.ToolBarArea.TopToolBarArea, self.toolbar)
        self.widget_main = SolaireClientWidget()
        self.setCentralWidget(self.widget_main)
        self.status_bar = status_bar.StatusBar(self)
        self.addToolBar(QtCore.Qt.ToolBarArea.BottomToolBarArea, self.status_bar)

        self.update_theme()

    def _register_subscribers(self) -> None:
        broker.register_subscriber(
            'window',
            'toggle_full_screen',
            self.toggle_fullscreen
        )
        broker.register_subscriber(
            'SYSTEM',
            'PREFERENCES_UPDATED',
            self.update_theme
        )

    def toggle_fullscreen(self, _: broker.Event = broker.DUMMY_EVENT) -> None:
        if not self._is_fullscreen:
            self.showFullScreen()
        else:
            self.showNormal()

        self._is_fullscreen = not self._is_fullscreen

    def update_theme(self, _: broker.Event = broker.DUMMY_EVENT) -> None:
        loaded_theme = appdata.Preferences().theme.theme_file
        theme_file = Path(theme.default_themes[loaded_theme])
        QtWrappers.set_style(self, theme_file)
