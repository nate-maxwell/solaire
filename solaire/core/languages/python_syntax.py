from dataclasses import dataclass

from PySide6 import QtGui
from PySide6 import QtCore
from PySide6TK import QtWrappers

from solaire.core import appdata


@dataclass
class PythonSyntaxColors(object):
    colors = appdata.Preferences().python_code_color
    keyword = QtWrappers.color_format(colors.keyword)
    operator = QtWrappers.color_format(colors.operator)
    brace = QtWrappers.color_format(colors.brace)
    string = QtWrappers.color_format(colors.string_single)
    string2 = QtWrappers.color_format(colors.string_triple)
    comment = QtWrappers.color_format(colors.comment, 'italic')
    numbers = QtWrappers.color_format(colors.numbers)

    def_ = QtWrappers.color_format(colors.def_)
    class_ = QtWrappers.color_format(colors.class_)
    self_ = QtWrappers.color_format(colors.self_)


_color_scheme = PythonSyntaxColors()


class PythonHighlighter(QtGui.QSyntaxHighlighter):
    """
    Syntax highlighter for the Python language that uses
    QtWrappers.HighlightRule.
    """

    # Keywords
    keywords = [
        'and', 'assert', 'break', 'class', 'continue', 'def',
        'del', 'elif', 'else', 'except', 'exec', 'finally',
        'for', 'from', 'global', 'if', 'import', 'in',
        'is', 'lambda', 'not', 'or', 'pass', 'print',
        'raise', 'return', 'try', 'while', 'yield',
        'None', 'True', 'False'
    ]

    # Operators
    operators = [
        '=',
        # Comparison
        '==', '!=', '<', '<=', '>', '>=',
        # Arithmetic
        r'\+', '-', r'\*', '/', '//', r'\%', r'\*\*',
        # In-place
        r'\+=', '-=', r'\*=', '/=', r'\%=',
        # Bitwise
        r'\^', r'\|', r'\&', r'\~', '>>', '<<'
    ]

    # Braces
    braces = [r'\{', r'\}', r'\(', r'\)', r'\[', r'\]']

    def __init__(self, parent: QtGui.QTextDocument | None = None) -> None:
        """
        Build regex rules and initialize multiline string handling.

        Args:
            parent: Optional text document parent.
        """
        super().__init__(parent)

        # Multi-line strings (delimiter regex, state id, style)
        self.tri_single = (QtCore.QRegularExpression(r"[']{3}"), 1, _color_scheme.string2)
        self.tri_double = (QtCore.QRegularExpression(r'["]{3}'), 2, _color_scheme.string2)

        # Track triple quotes that occur inside single-line strings so we can
        # skip them in block highlighting.
        self.trip_quote_within_strings: list[int] = []

        # Assemble QtWrappers.HighlightRule objects
        rules: list[QtWrappers.HighlightRule] = []

        # Keywords, operators, braces (whole-match = group 0)
        rules += [QtWrappers.HighlightRule(rf'\b{w}\b', _color_scheme.keyword, group=0) for w in PythonHighlighter.keywords]
        rules += [QtWrappers.HighlightRule(o, _color_scheme.operator, group=0) for o in PythonHighlighter.operators]
        rules += [QtWrappers.HighlightRule(b, _color_scheme.brace, group=0) for b in PythonHighlighter.braces]

        # Specific tokens
        rules += [
            # self
            QtWrappers.HighlightRule(r'\bself\b', _color_scheme.self_, group=0),

            # 'def' / 'class' followed by an identifier (capture group 1)
            QtWrappers.HighlightRule(r'\bdef\b\s*(\w+)', _color_scheme.def_, group=1),
            QtWrappers.HighlightRule(r'\bclass\b\s*(\w+)', _color_scheme.class_, group=1),

            # Numbers
            QtWrappers.HighlightRule(r'\b[+-]?[0-9]+[lL]?\b', _color_scheme.numbers, group=0),
            QtWrappers.HighlightRule(r'\b[+-]?0[xX][0-9A-Fa-f]+[lL]?\b', _color_scheme.numbers, group=0),
            QtWrappers.HighlightRule(r'\b[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\b', _color_scheme.numbers, group=0),

            # Strings
            QtWrappers.HighlightRule(r'"[^"\\]*(\\.[^"\\]*)*"', _color_scheme.string, group=0),
            QtWrappers.HighlightRule(r"'[^'\\]*(\\.[^'\\]*)*'", _color_scheme.string, group=0),

            # Comments
            QtWrappers.HighlightRule(r'#[^\n]*', _color_scheme.comment, group=0),
        ]

        self.rules: list[QtWrappers.HighlightRule] = rules

    def highlightBlock(self, text: str) -> None:
        """
        Apply syntax highlighting to one block (line) of text.

        Args:
            text: The text block to highlight.
        """

        string_rule_patterns = {
            r'"[^"\\]*(\\.[^"\\]*)*"',
            r"'[^'\\]*(\\.[^'\\]*)*'"
        }

        # First pass: detect embedded triple quotes within single-line strings
        for rule in self.rules:
            if rule.pattern.pattern() not in string_rule_patterns:
                continue
            it = rule.pattern.globalMatch(text, 0)
            while it.hasNext():
                m = it.next()
                start0 = m.capturedStart(0)
                if start0 < 0:
                    continue
                ii = self.tri_single[0].match(text, start0 + 1).capturedStart(0)
                if ii == -1:
                    ii = self.tri_double[0].match(text, start0 + 1).capturedStart(0)
                if ii != -1:
                    self.trip_quote_within_strings.extend((ii, ii + 1, ii + 2))

        # Second pass: apply all QtWrappers.HighlightRule-based patterns
        for rule in self.rules:
            it = rule.pattern.globalMatch(text, 0)
            while it.hasNext():
                m = it.next()
                start = m.capturedStart(rule.group)
                length = m.capturedLength(rule.group)

                # Fallback to whole match if the capture group is missing
                if start < 0 or length <= 0:
                    start = m.capturedStart(0)
                    length = m.capturedLength(0)

                if start < 0 or length <= 0:
                    continue

                # Skip characters that are part of embedded triple-quote tokens
                if start in self.trip_quote_within_strings:
                    continue

                self.setFormat(start, length, rule.format)

        self.setCurrentBlockState(0)

        # Handle multi-line strings
        in_multiline = self.match_multiline(text, *self.tri_single)
        if not in_multiline:
            self.match_multiline(text, *self.tri_double)

    def match_multiline(
        self,
        text: str,
        delimiter: QtCore.QRegularExpression,
        in_state: int,
        style: QtGui.QTextCharFormat
    ) -> bool:
        """
        Highlight multi-line triple-quoted strings.

        Args:
            text: The text block to highlight within.
            delimiter: Regex for the triple-single/double-quote delimiter.
            in_state: Syntax highlighter block state id for being inside a string.
            style: Text format for multi-line strings.

        Returns:
            True if still inside a multi-line string after processing this block.
        """
        fmt = style

        # If we were already inside the delimiter on the previous line, start at 0
        if self.previousBlockState() == in_state:
            start = 0
            add = 0
        else:
            first_match = delimiter.match(text)
            start = first_match.capturedStart() if first_match.hasMatch() else -1
            # skip triple quotes that are inside single-line string tokens
            if start in self.trip_quote_within_strings:
                return False
            add = first_match.capturedLength() if first_match.hasMatch() else 0

        # Walk delimiters until we finish or run off the line
        while start >= 0:
            end_match = delimiter.match(text, start + add)
            end = end_match.capturedStart() if end_match.hasMatch() else -1

            if end >= add:
                length = end - start + add + (end_match.capturedLength() if end_match.hasMatch() else 0)
                self.setCurrentBlockState(0)
            else:
                self.setCurrentBlockState(in_state)
                length = len(text) - start + add

            self.setFormat(start, length, fmt)

            next_match = delimiter.match(text, start + length)
            start = next_match.capturedStart() if next_match.hasMatch() else -1
            add = next_match.capturedLength() if next_match.hasMatch() else 0

        return self.currentBlockState() == in_state
