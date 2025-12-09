from typing import Optional

from PySide6 import QtWidgets

from solaire.core import terminal


class OutputTabWidget(QtWidgets.QTabWidget):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.terminal = terminal.TerminalWidget(
            self,
            install_as_sys=True,
            tee_to_original=False
        )

        self.addTab(self.terminal, 'Terminal')
