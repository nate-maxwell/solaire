from typing import Optional

from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets
from PySide6TK import QtWrappers

from solaire.core import appdata


class ColorButton(QtWidgets.QPushButton):
    colorChanged = QtCore.Signal(QtGui.QColor)

    def __init__(
            self,
            color: str = '#ffffff',
            parent: Optional[QtWidgets.QWidget] = None
    ) -> None:
        super().__init__(parent)
        self._color = QtGui.QColor(color)
        self.setFixedSize(32, 18)
        self._update_style()
        self.clicked.connect(self.choose_color)

    def _update_style(self) -> None:
        self.setStyleSheet(f'background-color: {self._color.name()}; border: 1px solid #333;')

    def choose_color(self) -> None:
        color = QtWidgets.QColorDialog.getColor(self._color, self, 'Choose Color')
        if color.isValid():
            self._color = color
            self._update_style()
            self.colorChanged.emit(color)

    def color(self) -> QtGui.QColor:
        return self._color


class PreferenceTopicMenu(QtWrappers.ScrollArea):

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.prefs = appdata.Preferences()

    def sync_settings(self) -> None:
        raise NotImplementedError


class CodePreferencesMenu(PreferenceTopicMenu):

    def __init__(self) -> None:
        super().__init__('Code')
        self.topic_prefs = self.prefs.code_preferences

        self.tab_type = QtWrappers.LabeledComboBox('Tab Type')
        self.tab_type.add_items(['Space', 'Tab'])
        self.tab_type.set_current_text(self.topic_prefs.tab_type)
        self.add_widget(self.tab_type)

        self.tab_space_width = QtWrappers.LabeledSpinBox('Tab Space Width')
        self.tab_space_width.set_value(self.topic_prefs.tab_space_width)
        self.add_widget(self.tab_space_width)

        self.guide_column_enabled = QtWrappers.LabeledComboBox('Enable Vertical Guide')
        self.guide_column_enabled.add_items(['Enabled', 'Disabled'])
        self.add_widget(self.guide_column_enabled)

        self.guide_column = QtWrappers.LabeledSpinBox('Vertical Guide Column')
        self.guide_column.set_value(self.topic_prefs.guide_column)
        self.add_widget(self.guide_column)

        self.add_stretch()

    def sync_settings(self) -> None:
        self.topic_prefs.tab_type = self.tab_type.current_text()
        self.topic_prefs.tab_space_width = self.tab_space_width.value()

        guide_enabled = self.guide_column_enabled.current_text() == 'Enabled'
        self.topic_prefs.enable_vertical_guide = guide_enabled
        self.topic_prefs.guide_column = self.guide_column.value()


class PythonCodeColorMenu(PreferenceTopicMenu):

    def __init__(self) -> None:
        super().__init__('Python Color')
        self.topic_prefs = self.prefs.python_code_color

        self.glayout_colors = QtWrappers.GridLayout()
        self.add_layout(self.glayout_colors)

        self.glayout_colors.add_to_new_row(QtWidgets.QLabel('Keyword'))
        self.color_keyword = ColorButton(self.topic_prefs.keyword, self)
        self.glayout_colors.add_to_last_row(self.color_keyword)

        self.glayout_colors.add_to_new_row(QtWidgets.QLabel('Operator'))
        self.color_operator = ColorButton(self.topic_prefs.operator, self)
        self.glayout_colors.add_to_last_row(self.color_operator)

        self.glayout_colors.add_to_new_row(QtWidgets.QLabel('Brace'))
        self.color_brace = ColorButton(self.topic_prefs.brace, self)
        self.glayout_colors.add_to_last_row(self.color_brace)

        self.glayout_colors.add_to_new_row(QtWidgets.QLabel('String Single'))
        self.color_string_single = ColorButton(self.topic_prefs.string_single, self)
        self.glayout_colors.add_to_last_row(self.color_string_single)

        self.glayout_colors.add_to_new_row(QtWidgets.QLabel('String Triple'))
        self.color_string_triple = ColorButton(self.topic_prefs.string_triple, self)
        self.glayout_colors.add_to_last_row(self.color_string_triple)

        self.glayout_colors.add_to_new_row(QtWidgets.QLabel('Comment'))
        self.color_comment = ColorButton(self.topic_prefs.comment, self)
        self.glayout_colors.add_to_last_row(self.color_comment)

        self.glayout_colors.add_to_new_row(QtWidgets.QLabel('Numbers'))
        self.color_numbers = ColorButton(self.topic_prefs.numbers, self)
        self.glayout_colors.add_to_last_row(self.color_numbers)

        self.glayout_colors.add_to_new_row(QtWidgets.QLabel('def'))
        self.color_def = ColorButton(self.topic_prefs.def_, self)
        self.glayout_colors.add_to_last_row(self.color_def)

        self.glayout_colors.add_to_new_row(QtWidgets.QLabel('class'))
        self.color_class = ColorButton(self.topic_prefs.class_, self)
        self.glayout_colors.add_to_last_row(self.color_class)

        self.glayout_colors.add_to_new_row(QtWidgets.QLabel('self'))
        self.color_self = ColorButton(self.topic_prefs.self_, self)
        self.glayout_colors.add_to_last_row(self.color_self)

        self.add_stretch()

    def sync_settings(self) -> None:
        self.topic_prefs.keyword = self.color_keyword.color().name()
        self.topic_prefs.operator = self.color_operator.color().name()
        self.topic_prefs.brace = self.color_brace.color().name()
        self.topic_prefs.string_single = self.color_string_single.color().name()
        self.topic_prefs.string_triple = self.color_string_triple.color().name()
        self.topic_prefs.comment = self.color_comment.color().name()
        self.topic_prefs.numbers = self.color_def.color().name()
        self.topic_prefs.self_ = self.color_self.color().name()


class JsonCodeColorMenu(PreferenceTopicMenu):

    def __init__(self) -> None:
        super().__init__('JSON Color')
        self.topic_prefs = self.prefs.json_code_color

        self.glayout_colors = QtWrappers.GridLayout()
        self.add_layout(self.glayout_colors)

        self.glayout_colors.add_to_new_row(QtWidgets.QLabel('Numeric'))
        self.color_numeric = ColorButton(self.topic_prefs.numeric, self)
        self.glayout_colors.add_to_last_row(self.color_numeric)

        self.glayout_colors.add_to_new_row(QtWidgets.QLabel('Key'))
        self.color_key = ColorButton(self.topic_prefs.key, self)
        self.glayout_colors.add_to_last_row(self.color_key)

        self.glayout_colors.add_to_new_row(QtWidgets.QLabel('Value'))
        self.color_value = ColorButton(self.topic_prefs.value, self)
        self.glayout_colors.add_to_last_row(self.color_value)

        self.add_stretch()

    def sync_settings(self) -> None:
        self.topic_prefs.numeric = self.color_numeric.color().name()
        self.topic_prefs.key = self.color_key.color().name()
        self.topic_prefs.value = self.color_value.color().name()


class RefreshPreferencesMenu(PreferenceTopicMenu):
    def __init__(self) -> None:
        super().__init__('Refresh')
        self.topic_prefs = self.prefs.refresh

        self.cursor = QtWrappers.LabeledSpinBox('Cursor')
        self.cursor.set_value(self.topic_prefs.cursor)
        self.add_widget(self.cursor)

        self.code_fold = QtWrappers.LabeledSpinBox('Code Folding')
        self.code_fold.set_value(self.topic_prefs.code_fold)
        self.add_widget(self.code_fold)

        self.add_stretch()

    def sync_settings(self) -> None:
        self.topic_prefs.cursor = self.cursor.value()
        self.topic_prefs.code_fold = self.code_fold.value()


class PreferencesMenu(QtWrappers.MainWindow):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__('Preferences', parent=parent)
        self.settings_before = appdata.Preferences().to_dict()

        self._create_widgets()
        self._create_layout()
        self._create_connections()

    def _create_widgets(self) -> None:
        self.widget_main = QtWidgets.QWidget()
        self.layout_main = QtWidgets.QVBoxLayout()

        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)

        self.stack_topics = QtWidgets.QStackedWidget()
        self.code_preferences_settings = CodePreferencesMenu()
        self.python_code_color_settings = PythonCodeColorMenu()
        self.json_code_color_settings = JsonCodeColorMenu()
        self.refresh_settings = RefreshPreferencesMenu()

        self.sa_topics = QtWrappers.ScrollArea()
        self.btn_code_preferences = QtWidgets.QPushButton('Code Preferences')
        self.btn_python_colors = QtWidgets.QPushButton('Python Syntax Colors')
        self.btn_json_colors = QtWidgets.QPushButton('JSON Syntax Colors')
        self.btn_refresh = QtWidgets.QPushButton('Refresh Preferences')

        self.hlayout_actions = QtWidgets.QHBoxLayout()
        self.btn_ok = QtWidgets.QPushButton('Ok')
        self.btn_ok.setFixedWidth(100)
        self.btn_cancel = QtWidgets.QPushButton('Cancel')
        self.btn_cancel.setFixedWidth(100)
        self.btn_apply = QtWidgets.QPushButton('Apply')
        self.btn_apply.setFixedWidth(100)

    def _create_layout(self) -> None:
        # Topics
        self.stack_topics.addWidget(self.code_preferences_settings)
        self.stack_topics.addWidget(self.python_code_color_settings)
        self.stack_topics.addWidget(self.json_code_color_settings)
        self.stack_topics.addWidget(self.refresh_settings)
        self.stack_topics.addWidget(QtWrappers.VerticalSpacer())
        self.stack_topics.setCurrentIndex(0)

        self.sa_topics.add_widget(self.btn_code_preferences)
        self.sa_topics.add_widget(self.btn_python_colors)
        self.sa_topics.add_widget(self.btn_json_colors)
        self.sa_topics.add_widget(self.btn_refresh)
        self.sa_topics.add_widget(QtWrappers.VerticalSpacer())

        # Splitter
        self.splitter.addWidget(self.sa_topics)
        self.splitter.addWidget(self.stack_topics)

        # Action buttons
        self.hlayout_actions.addStretch()
        self.hlayout_actions.addWidget(self.btn_ok)
        self.hlayout_actions.addWidget(self.btn_cancel)
        self.hlayout_actions.addWidget(self.btn_apply)

        # Main
        self.setCentralWidget(self.widget_main)
        self.widget_main.setLayout(self.layout_main)
        self.layout_main.addWidget(self.splitter)
        self.layout_main.addLayout(self.hlayout_actions)

    def _create_connections(self) -> None:
        self.btn_ok.clicked.connect(self.ok)
        self.btn_cancel.clicked.connect(self.cancel)
        self.btn_apply.clicked.connect(self.apply)

        self.btn_code_preferences.clicked.connect(
            lambda: self.stack_topics.setCurrentWidget(self.code_preferences_settings)
        )
        self.btn_python_colors.clicked.connect(
            lambda: self.stack_topics.setCurrentWidget(self.python_code_color_settings)
        )
        self.btn_json_colors.clicked.connect(
            lambda: self.stack_topics.setCurrentWidget(self.json_code_color_settings)
        )
        self.btn_refresh.clicked.connect(
            lambda: self.stack_topics.setCurrentWidget(self.refresh_settings)
        )

    def _sync_settings(self) -> None:
        self.code_preferences_settings.sync_settings()
        self.python_code_color_settings.sync_settings()
        self.json_code_color_settings.sync_settings()
        self.refresh_settings.sync_settings()

    def ok(self) -> None:
        self._sync_settings()
        appdata.Preferences().save()

    def apply(self) -> None:
        self._sync_settings()
        appdata.Preferences().save()

        global window
        window = None
        self.close()
        self.deleteLater()

    def cancel(self) -> None:
        global window
        window = None

        prefs = appdata.Preferences()
        prefs.from_dict(self.settings_before)
        self.close()
        self.deleteLater()


window: Optional[PreferencesMenu] = None


def show_preferences_widget(parent: Optional[QtWidgets.QWidget] = None) -> None:
    """Show the singleton preferences widget."""
    global window
    if window is None:
        window = PreferencesMenu(parent)

    window.show()
