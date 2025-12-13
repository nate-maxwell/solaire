"""
Status bar at the bottom of the application.
This status bar is not meant to allow users to change settings, but rather
simply display application data and preference values.
"""


from PySide6 import QtWidgets
from PySide6TK import QtWrappers

from solaire.core import appdata
from solaire.core import broker


class StatusBar(QtWrappers.Toolbar):
    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__('StatusBar', parent)

        broker.register_subscriber(
            'code_editor',
            'cursor_position',
            self.cursor_changed_subscription
        )
        broker.register_subscriber(
            'SYSTEM',
            'PREFERENCES_UPDATED',
            self.on_appdata_changed
        )

    def build(self) -> None:
        self.addWidget(QtWrappers.VerticalSpacer(16))

        self.add_toolbar_separator(0)

        self.lbl_cursor = QtWidgets.QLabel('')
        self.addWidget(self.lbl_cursor)
        self.add_line()

        self.lbl_encoding = QtWidgets.QLabel('UTF-8')
        self.addWidget(self.lbl_encoding)
        self.add_line()

        self.lbl_tab_type = QtWidgets.QLabel('4 spaces')
        self.addWidget(self.lbl_tab_type)
        self.add_line()

    def add_line(self) -> None:
        width = 16
        self.add_toolbar_separator(width)
        self.addWidget(QtWrappers.VerticalLine())
        self.add_toolbar_separator(width)

    def cursor_changed_subscription(self, event: broker.Event) -> None:
        line = event.data[0]
        col = event.data[1]
        self.lbl_cursor.setText(f'{line}:{col}')

    def on_appdata_changed(self, _: broker.Event) -> None:
        prefs = appdata.Preferences().code_preferences
        if prefs.tab_type == appdata.TAB_TYPE_SPACE:
            self.lbl_tab_type.setText(f'{prefs.tab_space_width} spaces')
        elif prefs.tab_type == appdata.TAB_TYPE_TAB:
            self.lbl_tab_type.setText('Tab')
        else:
            raise appdata.AppdataError('Unknown tab type from preferences!')
