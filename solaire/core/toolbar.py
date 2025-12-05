from PySide6TK import QtWrappers


class SolaireToolbar(QtWrappers.Toolbar):
    def __init__(self) -> None:
        super().__init__('SolaireToolbar', self)

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
