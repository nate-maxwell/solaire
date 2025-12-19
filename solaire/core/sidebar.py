"""
A container for all various menus placed to the left of the editor.

This is the designated area for non-floating menus for auxiliary tools in the
main IDE. These tools range from the file explorer, to the structure outline
of the active tab's code, to a git menu, etc.
"""


from pathlib import Path
from typing import Optional

from PySide6 import QtCore
from PySide6 import QtWidgets

from solaire.components.file_explorer import SolaireFileTree
from solaire.components.structure_explorer import CodeStructureWidget
from solaire.components.git import GitWidget
from solaire.core import broker


class SideBar(QtWidgets.QWidget):
    """
    An all-purpose container widget for non-floating tools and menus that are
    toggled in visibility, located to the left of the main code editing area.
    """

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.layout_main = QtWidgets.QVBoxLayout()
        self.layout_main.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout_main)

        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        self.layout_main.addWidget(self.splitter)

        self.add_widget(SolaireFileTree(parent=self), 'toggle_explorer')
        self.add_widget(CodeStructureWidget(parent=self), 'toggle_structure')

        temp_path = Path(__file__).parent.parent.parent
        self.add_widget(GitWidget(temp_path, parent=self), 'toggle_git')

    def add_widget(
            self,
            wid: QtWidgets.QWidget,
            visibility_even_name: str
    ) -> None:
        """
        Adds a widget in first-come first-add order to the splitter.
        Hooks widget visibility to the event broker using the given visibility
        event name.
        """
        self.splitter.addWidget(wid)

        visibility_func: broker.END_POINT = lambda _ : wid.setVisible(not wid.isVisible())
        broker.register_subscriber(
            'side_bar',
            visibility_even_name,
            visibility_func
        )
