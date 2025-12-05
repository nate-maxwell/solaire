from PySide6 import QtWidgets


class FileExplorer(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)

        self._create_widgets()
        self._create_layout()
        self._create_connections()

    def _create_widgets(self) -> None:
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.header_label = QtWidgets.QLabel('Explorer')
        # self.header_label.setSizePolicy(
        #     QtWidgets.QSizePolicy.Policy.Expanding,
        #     QtWidgets.QSizePolicy.Policy.Preferred
        # )
        # self.header_label.setFixedHeight(20)

    def _create_layout(self) -> None:
        self.setLayout(self.layout)

        self.layout.addWidget(self.header_label)
        self.layout.addStretch()

    def _create_connections(self) -> None:
        ...
