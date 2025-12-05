from PySide6 import QtWidgets
from PySide6TK import QtWrappers


class StatusBar(QtWrappers.Toolbar):
    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__('StatusBar', parent)

    def build(self) -> None:
        # Temp to add anything for status bar visibility
        self.addWidget(QtWrappers.VerticalSpacer(10))
