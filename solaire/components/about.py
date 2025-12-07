import webbrowser
from typing import Optional

from PySide6 import QtWidgets
from PySide6TK import QtWrappers

from solaire.core import resources


repo_url = 'https://github.com/nate-maxwell/solaire'
documentation_url = 'https://github.com/nate-maxwell/solaire'

about_1 = """Solaire is a text editor, primarily for writing python code in
art production DCCs.
"""
about_2 = 'Developed by Nate Maxwell.'
abouts = [about_1, about_2]


class AboutWidget(QtWidgets.QMainWindow):
    """Simple widget showing the about-info of the editor."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle('About')

        self._create_widgets()
        self._create_layout()
        self._create_connections()

    def _create_widgets(self) -> None:
        self.widget_main = QtWidgets.QWidget()
        self.layout_main = QtWidgets.QHBoxLayout()

        self.logo = QtWrappers.PreviewImage('')
        self.logo.set_source(resources.LOGO_PATH)

        self.vlayout_about = QtWidgets.QVBoxLayout()

        self.hlayout_buttons = QtWidgets.QHBoxLayout()
        self.btn_documentation = QtWidgets.QPushButton('Documentation')
        self.btn_repo = QtWidgets.QPushButton('Repo')

    def _create_layout(self) -> None:
        self.hlayout_buttons.addWidget(self.btn_documentation)
        self.hlayout_buttons.addWidget(self.btn_repo)

        for i in abouts:
            label = QtWidgets.QLabel(i)
            self.vlayout_about.addWidget(label)
        self.vlayout_about.addLayout(self.hlayout_buttons)

        self.setCentralWidget(self.widget_main)
        self.widget_main.setLayout(self.layout_main)
        self.layout_main.addWidget(self.logo)
        self.layout_main.addLayout(self.vlayout_about)

    def _create_connections(self) -> None:
        self.btn_repo.clicked.connect(
            lambda: webbrowser.open_new_tab(repo_url)
        )
        self.btn_documentation.clicked.connect(
            lambda: webbrowser.open_new_tab(documentation_url)
        )


about_widget: Optional[AboutWidget] = None


def show_about_widget(parent: Optional[QtWidgets.QWidget] = None) -> None:
    """Show the singleton about widget."""
    global about_widget
    if about_widget is None:
        about_widget = AboutWidget(parent)

    about_widget.show()
