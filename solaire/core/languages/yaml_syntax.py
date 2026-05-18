from dataclasses import dataclass
from dataclasses import field
from functools import partial
from typing import Optional

from PySide6 import QtGui
from PySide6TK import QtWrappers

from solaire.core import appdata


def _fmt(key: str, *styles: str) -> QtGui.QTextCharFormat:
    """Build a QTextCharFormat from current prefs for a given key."""
    colors = appdata.Preferences().yaml_code_color  # live snapshot
    return QtWrappers.color_format(getattr(colors, key), *styles)


@dataclass
class YamlSyntaxColors:
    key: QtGui.QTextCharFormat = field(default_factory=partial(_fmt, "key"))
    value: QtGui.QTextCharFormat = field(default_factory=partial(_fmt, "value"))
    numeric: QtGui.QTextCharFormat = field(default_factory=partial(_fmt, "numeric"))
    constant: QtGui.QTextCharFormat = field(default_factory=partial(_fmt, "constant"))
    comment: QtGui.QTextCharFormat = field(
        default_factory=partial(_fmt, "comment", "italic")
    )
    anchor: QtGui.QTextCharFormat = field(default_factory=partial(_fmt, "anchor"))
    tag: QtGui.QTextCharFormat = field(default_factory=partial(_fmt, "tag"))
    indicator: QtGui.QTextCharFormat = field(default_factory=partial(_fmt, "indicator"))
    document: QtGui.QTextCharFormat = field(default_factory=partial(_fmt, "document"))


_color_scheme = YamlSyntaxColors()


def reload_color_scheme() -> None:
    global _color_scheme
    _color_scheme = YamlSyntaxColors()


class YamlHighlighter(QtGui.QSyntaxHighlighter):
    """Syntax highlighter for YAML that uses QtWrappers.HighlightRule."""

    def __init__(self, parent: Optional[QtGui.QTextDocument] = None) -> None:
        """
        Build regex rules for YAML tokens.

        Args:
            parent: Optional text document parent.
        """
        super().__init__(parent)

        rules: list[QtWrappers.HighlightRule] = []

        # Document markers: --- and ...
        document_pattern = r"^(?:---|\.\.\.)\s*$"
        rules.append(
            QtWrappers.HighlightRule(document_pattern, _color_scheme.document, group=0)
        )

        # List indicator: leading dash followed by whitespace
        list_pattern = r"^\s*(-)(?=\s)"
        rules.append(
            QtWrappers.HighlightRule(list_pattern, _color_scheme.indicator, group=1)
        )

        # Block scalar indicators: | or > optionally with chomp/indent (|-, >+, |2-)
        block_scalar_pattern = r":\s*([|>][+-]?\d?[+-]?)\s*$"
        rules.append(
            QtWrappers.HighlightRule(
                block_scalar_pattern, _color_scheme.indicator, group=1
            )
        )

        # Flow-style indicators: { } [ ] ,
        flow_pattern = r"[{}\[\],]"
        rules.append(
            QtWrappers.HighlightRule(flow_pattern, _color_scheme.indicator, group=0)
        )

        # Tags: !!type or !Custom
        tag_pattern = r"(![!\w][\w./-]*)"
        rules.append(QtWrappers.HighlightRule(tag_pattern, _color_scheme.tag, group=1))

        # Anchors and aliases: &name or *name
        anchor_pattern = r"([&*][A-Za-z_][\w-]*)"
        rules.append(
            QtWrappers.HighlightRule(anchor_pattern, _color_scheme.anchor, group=1)
        )

        # Keys: quoted ("foo": / 'foo':) or unquoted (foo:). Allows a leading
        # "- " for list-of-mappings without painting the dash itself.
        # Group 1 = whole key including quotes; backreference \2 matches the
        # opening quote (or empty for unquoted keys).
        key_pattern = (
            r'^(?:\s*-\s+)?(("|\')?[^"\'\s\-{}\[\],&*!#][^:\n]*?\2)\s*:(?=\s|$)'
        )
        rules.append(QtWrappers.HighlightRule(key_pattern, _color_scheme.key, group=1))

        # Constants: true/false/yes/no/on/off/null/~ as standalone values
        constant_pattern = r":\s*(true|false|yes|no|on|off|null|~|True|False|Null|TRUE|FALSE|NULL)(?=\s|,|]|}|$)"
        rules.append(
            QtWrappers.HighlightRule(constant_pattern, _color_scheme.constant, group=1)
        )

        # Numbers: ints, floats, scientific, hex, octal as values
        numeric_pattern = (
            r":\s*([-+]?"
            r"(?:0x[0-9A-Fa-f]+"
            r"|0o[0-7]+"
            r"|\d+(?:\.\d+)?(?:[eE][-+]?\d+)?"
            r"|\.inf|\.nan)"
            r")(?=\s|,|]|}|$)"
        )
        rules.append(
            QtWrappers.HighlightRule(numeric_pattern, _color_scheme.numeric, group=1)
        )

        # Quoted string values
        rules.append(
            QtWrappers.HighlightRule(
                r':\s*("[^"\\]*(?:\\.[^"\\]*)*")', _color_scheme.value, group=1
            )
        )
        rules.append(
            QtWrappers.HighlightRule(
                r":\s*('[^'\\]*(?:\\.[^'\\]*)*')", _color_scheme.value, group=1
            )
        )

        # Comments: # to end of line. Placed last so it overrides earlier rules
        # that may have matched inside the comment region.
        rules.append(
            QtWrappers.HighlightRule(r"#[^\n]*", _color_scheme.comment, group=0)
        )

        self.rules: list[QtWrappers.HighlightRule] = rules

    def highlightBlock(self, text: str) -> None:
        """
        Apply syntax highlighting to one block (line) of text.

        Args:
            text: The text block to highlight.
        """
        comment_start = self._find_comment_start(text)

        for rule in self.rules:
            it = rule.pattern.globalMatch(text)
            while it.hasNext():
                m = it.next()
                start = m.capturedStart(rule.group)
                length = m.capturedLength(rule.group)
                if start < 0 or length <= 0:
                    continue
                # Skip matches that fall inside a comment (except the comment
                # rule itself, which targets the comment region).
                if (
                    comment_start >= 0
                    and start >= comment_start
                    and rule.format is not _color_scheme.comment
                ):
                    continue
                self.setFormat(start, length, rule.format)

    @staticmethod
    def _find_comment_start(text: str) -> int:
        """
        Locate the first '#' that introduces a comment, ignoring '#' inside
        quoted strings.

        Args:
            text: The text block to scan.

        Returns:
            int: Index of the comment start, or -1 if no comment exists.
        """
        in_single = False
        in_double = False
        i = 0
        n = len(text)
        while i < n:
            ch = text[i]
            if ch == "\\" and (in_single or in_double) and i + 1 < n:
                i += 2
                continue
            if ch == '"' and not in_single:
                in_double = not in_double
            elif ch == "'" and not in_double:
                in_single = not in_single
            elif ch == "#" and not in_single and not in_double:
                # '#' only starts a comment when preceded by whitespace or BOL
                if i == 0 or text[i - 1].isspace():
                    return i
            i += 1
        return -1
