from dataclasses import dataclass
from dataclasses import field
from functools import partial

from PySide6 import QtGui
from PySide6TK import QtWrappers

from solaire.core import appdata


def _fmt(key: str, *styles: str) -> QtGui.QTextCharFormat:
    """Build a QTextCharFormat from current prefs for a given key."""
    colors = appdata.Preferences().json_code_color  # live snapshot
    return QtWrappers.color_format(getattr(colors, key), *styles)


@dataclass
class JsonSyntaxColors:
    numerical: QtGui.QTextCharFormat = field(default_factory=partial(_fmt, 'numeric'))
    keys: QtGui.QTextCharFormat = field(default_factory=partial(_fmt, 'key'))
    values: QtGui.QTextCharFormat = field(default_factory=partial(_fmt, 'value'))


_color_scheme = JsonSyntaxColors()


def reload_color_scheme() -> None:
    global _color_scheme
    _color_scheme = JsonSyntaxColors()


class JsonHighlighter(QtGui.QSyntaxHighlighter):
    def __init__(self, parent=None) -> None:
        """Initialize rules with expression pattern and text format."""
        super(JsonHighlighter, self).__init__(parent)

        self.rules = []

        numeric_pattern = r'([-0-9.]+)(?!([^"]*"\s*:))'
        self.rules.append(
            QtWrappers.HighlightRule(numeric_pattern, _color_scheme.numerical, group=1)
        )
        key_pattern = r'("([^"]*)")\s*:'
        self.rules.append(
            QtWrappers.HighlightRule(key_pattern, _color_scheme.keys, group=1)
        )
        value_pattern = r':\s*("([^"]*)")'
        self.rules.append(
            QtWrappers.HighlightRule(value_pattern, _color_scheme.values, group=1)
        )

    def highlightBlock(self, text: str) -> None:
        """
        Implement the text block highlighting using QRegularExpression.

        Args:
            text: The text to perform a keyword highlighting check on.
        """
        for rule in self.rules:
            it = rule.pattern.globalMatch(text)
            while it.hasNext():
                m = it.next()
                start = m.capturedStart(rule.group)
                length = m.capturedLength(rule.group)
                if start >= 0 and length > 0:
                    self.setFormat(start, length, rule.format)
