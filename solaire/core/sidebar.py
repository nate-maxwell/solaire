"""
A container for all various menus placed to the left of the editor.

This is the designated area for non-floating menus for auxiliary tools in the
main IDE. These tools range from the file explorer, to the structure outline
of the active tab's code, to a git menu, etc.
"""


from typing import Optional

from PySide6 import QtCore
from PySide6 import QtWidgets

from solaire.core import broker
from solaire.core import file_explorer
from solaire.core import structure_explorer


class WidgetShelf(QtWidgets.QWidget):
    """Project file explorer. Supports creating and saving files and folders.
    Creating folders will not affect the loaded project directory.
    """

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self._create_widgets()
        self._create_layout()
        self._create_subscriptions()

    def _create_widgets(self) -> None:
        self.layout_main = QtWidgets.QVBoxLayout()
        self.layout_main.setContentsMargins(0, 0, 0, 0)
        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)

        self.file_explorer = file_explorer.SolaireFileTree(self)
        self.structure_explorer = structure_explorer.CodeStructureWidget(self)
        self.structure_explorer.setVisible(False)

    def _create_layout(self) -> None:
        self.splitter.addWidget(self.file_explorer)
        self.splitter.addWidget(self.structure_explorer)

        self.setLayout(self.layout_main)
        self.layout_main.addWidget(self.splitter)

    def _create_subscriptions(self) -> None:
        broker.register_subscriber(
            'sections_bar',
            'toggle_explorer',
            self.toggle_file_explorer_visibility
        )
        broker.register_subscriber(
            'sections_bar',
            'toggle_structure',
            self.toggle_structure_explorer_visibility
        )

    def toggle_file_explorer_visibility(
            self,
            _: broker.Event = broker.DUMMY_EVENT
    ) -> None:
        self.file_explorer.setVisible(not self.file_explorer.isVisible())

    def toggle_structure_explorer_visibility(
            self,
            _: broker.Event = broker.DUMMY_EVENT
    ) -> None:
        self.structure_explorer.setVisible(not self.structure_explorer.isVisible())
