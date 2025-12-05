from PySide6 import QtWidgets

from solaire.core import code_editor


class SolaireTabManager(QtWidgets.QTabWidget):
    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)

        self.dev_editor = code_editor.CodeEditor(self)
        self.addTab(self.dev_editor, 'Dev Editor')
