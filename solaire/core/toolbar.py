from PySide6 import QtWidgets
from PySide6TK import QtWrappers

from solaire.core import shortucts


class SolaireToolbar(QtWrappers.Toolbar):
    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__('SolaireToolbar', parent)
        self.setFixedHeight(22)
        self.setStyleSheet("""
            QToolButton::menu-indicator {
                image: none;
                width: 0px;
            }
        """)

    def build(self) -> None:
        self._file_section()
        self._edit_section()
        self._view_section()
        self._code_section()
        self._tools_section()
        self._preference_section()
        self._help_section()

    def _file_section(self) -> None:
        menu = self.add_menu('File')
        self.add_menu_command(
            menu,
            'Shortcuts',
            shortucts.shortcut_manager.show_editor
        )

    def _edit_section(self) -> None:
        menu = self.add_menu('Edit')

    def _view_section(self) -> None:
        menu = self.add_menu('View')

    def _code_section(self) -> None:
        menu = self.add_menu('Code')

    def _tools_section(self) -> None:
        menu = self.add_menu('Tools')

    def _preference_section(self) -> None:
        menu = self.add_menu('Preferences')

    def _help_section(self) -> None:
        menu = self.add_menu('Help')
        self.add_menu_command(menu, 'About')
