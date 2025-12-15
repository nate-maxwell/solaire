"""
The toolbar at the top of the application and each of the submenus.

Some menus may not have items in them but are placed as a reminder to fill
populate them later.
"""


from PySide6 import QtWidgets
from PySide6TK import QtWrappers

from solaire.core import common_events
from solaire.core import shortucts
from solaire.components import about
from solaire.components import preferences


class SolaireToolbar(QtWrappers.Toolbar):
    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__('SolaireToolbar', parent)
        self.setMinimumHeight(22)
        self.setMaximumHeight(26)
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
        self._preference_section()
        self._plugins_section()
        self._help_section()
        self._button_section()

    def _file_section(self) -> None:
        menu = self.add_menu('File')
        self.add_menu_command(menu, 'Open File', common_events.open_file)
        self.add_menu_command(menu, 'Open Folder', common_events.open_folder)
        self.add_menu_command(menu, 'Save', common_events.save_file)
        self.add_menu_command(menu, 'Save All', common_events.save_all)
        self.add_menu_command(menu, 'Quit', QtWidgets.QApplication.quit)

    def _edit_section(self) -> None:
        menu = self.add_menu('Edit')
        manager = shortucts.shortcut_manager
        self.add_menu_command(menu, 'Shortcuts', manager.show_editor)

    def _view_section(self) -> None:
        menu = self.add_menu('View')
        self.add_menu_command(
            menu, 'File Explorer', common_events.toggle_explorer
        )
        self.add_menu_command(
            menu, 'Structure', common_events.toggle_structure
        )

    def _code_section(self) -> None:
        menu = self.add_menu('Code')
        self.add_menu_command(menu, 'Run', common_events.run_code)

    def _preference_section(self) -> None:
        menu = self.add_menu('Preferences')
        self.add_menu_command(
            menu,
            'Preferences',
            lambda: preferences.show_preferences_widget(self)
        )

    def _plugins_section(self) -> None:
        menu = self.add_menu('Plugins')

    def _help_section(self) -> None:
        menu = self.add_menu('Help')
        self.add_menu_command(
            menu,
            'About',
            lambda: about.show_about_widget(self)
        )

    def _button_section(self) -> None:
        self.add_toolbar_separator(0)

        # Run button
        run_img = QtWidgets.QStyle.StandardPixmap.SP_MediaPlay
        run_icon = QtWidgets.QApplication.style().standardIcon(run_img)
        self.btn_run = QtWidgets.QPushButton(icon=run_icon)
        self.btn_run.clicked.connect(common_events.run_code)
        self.btn_run.setFixedWidth(50)
        self.addWidget(self.btn_run)

        self.add_toolbar_separator(20)
