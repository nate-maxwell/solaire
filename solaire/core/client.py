from typing import Optional

from PySide6 import QtWidgets
from PySide6TK import QtWrappers

import solaire.media


class SolaireClientWidget(QtWidgets.QWidget):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self._create_widgets()
        self._create_layout()
        self._create_connections()

    def _create_widgets(self) -> None:
        ...

    def _create_layout(self) -> None:
        ...

    def _create_connections(self) -> None:
        ...


class SolaireClientWindow(QtWrappers.MainWindow):
    def __init__(self) -> None:
        super().__init__('Solaire', icon_path=solaire.media.ICON_PATH)

        self.widget_main = SolaireClientWidget()
        self.setCentralWidget(self.widget_main)
