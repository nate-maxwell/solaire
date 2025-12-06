from PySide6 import QtWidgets

from solaire.core import code_editor


class SolaireTabManager(QtWidgets.QTabWidget):
    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)

        self.addTab(code_editor.CodeEditor(self), 'Script')
        self.addTab(code_editor.CodeEditor(self), 'Script2')
        self.addTab(code_editor.CodeEditor(self), 'Script3')
