"""
A QPlainTextEdit wrapper with numbered lines and syntax highlighting.
This is the primary "Editing Engine" of the program.

Uses a regex syntax highlighter.
"""


from dataclasses import dataclass
from typing import Optional

import PySide6TK.text
from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets
from PySide6TK.QtWrappers import CodeMiniMap

from solaire.core import broker
from solaire.core import languages
from solaire.core import timers
from solaire.core.languages.python_syntax import PythonHighlighter
from solaire.core.languages.python_syntax import reload_color_scheme

_INDENT = ' ' * 4
_COMMENT_PREFIX = '# '

_WRAPPING_PAIRS = {
    "'": "'",
    '"': '"',
    '(': ')',
    '[': ']',
    '{': '}',
    '`': '`',
}


broker.emit(broker.Event('SYSTEM', 'PREFERENCES_UPDATED'))


@dataclass
class _FoldRegion:
    """Represents a foldable region in the document."""
    start_block: int
    end_block: int
    is_folded: bool = False


class FoldArea(QtWidgets.QWidget):
    """Widget for displaying fold indicators."""

    def __init__(self, code_editor: 'CodeEditor') -> None:
        super().__init__(code_editor)
        self.editor = code_editor
        self.setMouseTracking(True)
        self._hover_block = -1

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(16, 0)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        self.editor.fold_area_paint_event(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        block_number = self.editor.get_block_number_at_pos(event.pos().y())
        if block_number != self._hover_block:
            self._hover_block = block_number
            self.update()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            block_number = self.editor.get_block_number_at_pos(event.pos().y())
            self.editor.toggle_fold(block_number)


class LineNumberArea(QtWidgets.QWidget):
    """
    A side-gutter widget responsible for rendering line numbers for a
    ``CodeEditor`` instance.

    Notes:
        - ``_LineNumberArea`` does not paint anything by itself; all
          drawing is delegated back to the parent editor.
        - ``sizeHint()`` returns a width based on the current block
          count so the gutter resizes correctly as line numbers grow
          into additional digits.
    """

    def __init__(self, code_editor: 'CodeEditor') -> None:
        super().__init__(code_editor)
        self.editor = code_editor

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(self.editor.line_number_area_width, 0)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        self.editor.line_number_area_paint_event(event)


optional_highlighter = Optional[languages.SyntaxHighlighter]


class CodeEditor(QtWidgets.QPlainTextEdit):
    """
    A custom code-editing widget built on top of ``QPlainTextEdit`` with
    line numbers, syntax highlighting, and indentation utilities.

    This editor provides an integrated gutter (``LineNumberArea``) that
    displays line numbers alongside the text viewport, updating
    automatically in response to scrolling, resizing, or block count
    changes. The editor also supports configurable syntax highlighting
    through a user-supplied ``QSyntaxHighlighter`` subclass
    (defaulting to ``PythonHighlighter``).

    Indentation and unindentation of multiple selected lines is supported
    through Tab and Shift+Tab. Two signals, ``indented`` and
    ``unindented``, emit a ``range`` of affected line numbers, allowing
    external tools to hook into indentation events if needed.

    Attributes:
        line_number_area (LineNumberArea):
            The side widget responsible for drawing line numbers.
        indented (Signal(range)):
            Emitted when a block of lines should be indented.
        unindented (Signal(range)):
            Emitted when a block of lines should be unindented.
        commented (signal(range)):
            Emitted when code is commented out.
        uncommented (signal(range)):
            Emitted when code is uncommented.
        folding_changed (Signal):
            Emitted whenever code is folded or unfolded.

    Args:
        syntax_highlighter_cls (SyntaxHighlighter, optional):
            A ``QSyntaxHighlighter`` subclass to use for syntax
            highlighting. Defaults to ``PythonHighlighter``.

    Notes:
        - Line numbers are recalculated dynamically based on the number
          of blocks in the document.
        - The currently active line is highlighted with a background
          marker for improved readability.
        - Prefix-based indentation functions are implemented to support
          both single-line and multi-line editing workflows.
    """

    indented = QtCore.Signal(range)
    unindented = QtCore.Signal(range)
    commented = QtCore.Signal(range)
    uncommented = QtCore.Signal(range)
    folding_changed = QtCore.Signal()

    column = 81 - 2
    guide_color = QtGui.QColor(70, 70, 70, 180)

    def __init__(
            self,
            parent: Optional[QtWidgets.QWidget] = None,
            syntax_highlighter_cls: optional_highlighter = PythonHighlighter
    ) -> None:
        super(CodeEditor, self).__init__(parent)

        self.setTabStopDistance(
            QtGui.QFontMetricsF(self.font()).horizontalAdvance(' ') * 4
        )

        self.line_number_area = LineNumberArea(self)
        self.fold_area = FoldArea(self)
        self._fold_regions: dict[int, _FoldRegion] = {}
        self.fold_area_width = 16

        # Add minimap to the right side
        self.minimap = CodeMiniMap(self, self)

        self._create_shortcut_signals()
        self._create_connections()
        self._create_subscriptions()
        self._create_fold_analyzer()
        self._create_cursor_timer()
        self.update_line_number_area_width(0)

        self.syntax_highlighter_cls = syntax_highlighter_cls
        self._highlighter: Optional[QtGui.QSyntaxHighlighter] = None
        if self.syntax_highlighter_cls is not None:
            self._highlighter = self.syntax_highlighter_cls(self.document())
        self.highlight_current_line()

        self.setFont(QtGui.QFont('Courier', 12))

    def _create_shortcut_signals(self) -> None:
        self.indented.connect(self.indent)
        self.unindented.connect(self.unindent)
        self.commented.connect(self.comment_lines)
        self.uncommented.connect(self.uncomment_lines)

    def _create_connections(self) -> None:
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)

    def _create_subscriptions(self) -> None:
        broker.register_subscriber(
            'structure_explorer',
            'item_clicked',
            lambda event: self.jump_to_line(event.data)
        )
        broker.register_subscriber(
            'SYSTEM',
            'PREFERENCES_UPDATED',
            self._on_preferences_updated
        )

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        cr = self.contentsRect()

        self.line_number_area.setGeometry(
            QtCore.QRect(
                cr.left(),
                cr.top(),
                self.line_number_area_width,
                cr.height()
            )
        )

        self.fold_area.setGeometry(
            QtCore.QRect(
                # Position next to line numbers
                cr.left() + self.line_number_area_width,
                cr.top(),
                self.fold_area_width,
                cr.height()
            )
        )

        # Position minimap on the right side
        minimap_width = self.minimap.width()
        self.minimap.setGeometry(
            QtCore.QRect(
                cr.right() - minimap_width,
                cr.top(),
                minimap_width,
                cr.height()
            )
        )

        self.line_number_area.raise_()
        self.fold_area.raise_()

    def paintEvent(self, event: QtGui.QPaintEvent):
        super().paintEvent(event)
        self._paint_guide()

    def jump_to_line(self, line_number: int) -> None:
        """Jump to a specific line in the editor."""
        cursor = self.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)
        cursor.movePosition(
            cursor.MoveOperation.Down,
            cursor.MoveMode.MoveAnchor,
            line_number - 1
        )
        self.setTextCursor(cursor)
        self.setFocus()

    def setPlainText(self, text, /) -> None:
        super().setPlainText(text)
        self.analyze_fold_regions()

    def _create_cursor_timer(self) -> None:
        self._cursor_timer = timers.create_bind_and_start_timer(
            self,
            16,
            self.cursorPositionChanged,
            self._emit_cursor_position
        )

    def _on_preferences_updated(self, _: broker.Event) -> None:
        reload_color_scheme()
        self._rebuilt_highlighter()

    def _rebuilt_highlighter(self) -> None:
        """Recreate the syntax highlighter for the current document."""
        if self._highlighter is None:
            return

        self._highlighter.setDocument(None)
        self._highlighter.deleteLater()
        self._highlighter = None

        if self.syntax_highlighter_cls is None:
            return

        self._highlighter = self.syntax_highlighter_cls(self.document())

    # -----Line Numbers--------------------------------------------------------

    @property
    def line_number_area_width(self) -> int:
        digits = 1
        count = max(1, self.blockCount())
        while count >= 10:
            count //= 10
            digits += 1
        space = 20 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def update_line_number_area_width(self, _) -> None:
        left_margin = self.line_number_area_width + self.fold_area_width
        right_margin = self.minimap.sizeHint().width()
        self.setViewportMargins(left_margin, 0, right_margin, 0)

    def update_line_number_area(
            self,
            rect: QtCore.QRect,
            vertical_scroll: int
    ) -> None:
        if vertical_scroll:
            self.line_number_area.scroll(0, vertical_scroll)
            self.fold_area.scroll(0, vertical_scroll)

            # Only update minimap when block position changes
            first_block = self.firstVisibleBlock().blockNumber()
            if first_block != getattr(self, '_last_minimap_block', -1):
                self.minimap.update()
            self._last_minimap_block = first_block
            return
        else:
            self.line_number_area.update(
                0,
                rect.y(),
                self.line_number_area.width(),
                rect.height()
            )
            self.fold_area.update(
                0,
                rect.y(),
                self.fold_area.width(),
                rect.height()
            )
            self.minimap.update()

        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    # -----Guide Ruler---------------------------------------------------------

    def _paint_guide(self) -> None:
        """Paints a common IDE vertical ruler for line length."""
        painter = QtGui.QPainter(self.viewport())
        painter.setPen(QtGui.QPen(self.guide_color, 1))

        # Average character width in current font
        fm = QtGui.QFontMetrics(self.font())
        char_width = fm.horizontalAdvance('M')

        x = self.column * char_width
        x -= self.horizontalScrollBar().value()

        # If visible in viewport...
        if 0 <= x <= self.viewport().width():
            painter.drawLine(x, 0, x, self.viewport().height())

        painter.end()

    # -----Code Folding--------------------------------------------------------

    def _create_fold_analyzer(self) -> None:
        self._fold_timer = timers.create_bind_and_start_timer(
            self,
            300,
            self.document().contentsChanged,
            self.analyze_fold_regions
        )

    def analyze_fold_regions(self) -> None:
        """Analyze document to find foldable regions.

        Supports:
            - Python indentation blocks (lines ending with ':')
            - Brace blocks     { ... }
            - Bracket blocks   [ ... ]
            - Paren blocks     ( ... )
        """
        self._fold_regions.clear()
        self._analyze_colon_blocks()
        self._analyze_paired_char_blocks()

    def _analyze_colon_blocks(self) -> None:
        # ---------- PYTHON ':' BLOCK FOLDING ----------
        doc = self.document()
        block = doc.firstBlock()
        while block.isValid():
            text = block.text()
            stripped = text.lstrip()

            if stripped and stripped.rstrip().endswith(':'):
                start_block = block.blockNumber()
                indent_level = len(text) - len(stripped)

                next_block = block.next()
                end_block = start_block

                while next_block.isValid():
                    next_text = next_block.text()
                    next_stripped = next_text.lstrip()

                    if not next_stripped:
                        next_block = next_block.next()
                        continue

                    next_indent = len(next_text) - len(next_stripped)
                    if next_indent <= indent_level:
                        break

                    end_block = next_block.blockNumber()
                    next_block = next_block.next()

                if end_block > start_block:
                    self._fold_regions[start_block] = _FoldRegion(
                        start_block=start_block,
                        end_block=end_block,
                        is_folded=False
                    )

            block = block.next()

    def _analyze_paired_char_blocks(self) -> None:
        # ---------- BRACE / BRACKET / PAREN MATCHING ----------
        doc = self.document()
        opening_tokens = {'{': '}', '[': ']', '(': ')'}
        stack = []  # (opening_char, block_number)

        block = doc.firstBlock()
        while block.isValid():
            text = block.text().rstrip()

            for i, ch in enumerate(text):
                if ch in opening_tokens:
                    # Opening symbol
                    stack.append((ch, block.blockNumber()))
                elif ch in opening_tokens.values():
                    # Closing symbol — match most recent open
                    if stack:
                        open_ch, open_block = stack[-1]
                        if opening_tokens[open_ch] == ch:
                            stack.pop()
                            close_block = block.blockNumber()

                            if close_block > open_block:
                                # Register fold region
                                # (Python ':' region may already exist — overwrite safely)
                                self._fold_regions[open_block] = _FoldRegion(
                                    start_block=open_block,
                                    end_block=close_block,
                                    is_folded=False
                                )

            block = block.next()

        self.fold_area.update()

    def toggle_fold(self, block_number: int) -> None:
        """Toggle folding at the given block number."""
        if block_number not in self._fold_regions:
            return

        region = self._fold_regions[block_number]
        region.is_folded = not region.is_folded

        doc = self.document()
        for i in range(region.start_block + 1, region.end_block + 1):
            block = doc.findBlockByNumber(i)
            block.setVisible(not region.is_folded)

        self.document().markContentsDirty(
            doc.findBlockByNumber(region.start_block).position(),
            doc.findBlockByNumber(region.end_block).position()
        )

        self.viewport().update()
        self.fold_area.update()
        self.line_number_area.update()

        self.folding_changed.emit()

    def fold_area_paint_event(self, event: QtGui.QPaintEvent) -> None:
        """Paint fold indicators."""
        painter = QtGui.QPainter(self.fold_area)
        painter.fillRect(event.rect(), QtGui.QColor(21, 21, 21))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        height = self.fontMetrics().height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                # Check if block has a fold region
                if block_number in self._fold_regions:
                    region = self._fold_regions[block_number]

                    # Draw fold tri
                    center_y = int(top + height / 2)
                    center_x = self.fold_area_width // 2
                    size = 6
                    half: int = size // 2

                    painter.setPen(QtGui.QPen(QtGui.QColor('lightGray'), 1))
                    painter.setBrush(QtGui.QColor('lightGray'))

                    if region.is_folded:
                        offsets = [(-half, -half), (-half, half), (half, 0)]
                    else:
                        offsets = [(-half, -half), (half, -half), (0, half)]

                    c = QtCore.QPoint(center_x, center_y)
                    qpt = QtCore.QPoint  # alias to avoid repeated attr lookups
                    triangle = [c + qpt(dx, dy) for dx, dy in offsets]
                    painter.drawPolygon(QtGui.QPolygon(triangle))

            block = block.next()
            if not block.isValid():
                break

            block_geo = self.blockBoundingGeometry(block)
            top = block_geo.translated(self.contentOffset()).top()
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1

    def get_block_number_at_pos(self, y_pos: int) -> int:
        """Get block number at a given Y position."""
        block = self.firstVisibleBlock()
        top = self.blockBoundingGeometry(block).translated(
            self.contentOffset()).top()

        while block.isValid():
            bottom = top + self.blockBoundingRect(block).height()
            if top <= y_pos < bottom:
                return block.blockNumber()
            block = block.next()
            top = bottom

        return -1

    # -----Paint/Colors--------------------------------------------------------

    def line_number_area_paint_event(self, event: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QtGui.QColor(21, 21, 21))  # Background color

        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        block_geo = self.blockBoundingGeometry(block)
        top = block_geo.translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        height = self.fontMetrics().height()
        while block.isValid() and (top <= event.rect().bottom()):
            if block.isVisible() and (bottom >= event.rect().top()):
                number = str(blockNumber + 1)
                painter.setPen(QtGui.QColor('lightGray'))
                painter.drawText(
                    0,
                    top,
                    self.line_number_area.width(),
                    height,
                    QtCore.Qt.AlignmentFlag.AlignLeft,
                    number
                )

            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            blockNumber += 1

    def _emit_cursor_position(self) -> None:
        """On cursor position change, update the highlighted line to the new
        current line and emit the new cursor line + col through the broker.
        """
        self.highlight_current_line()

        cursor = self.textCursor()
        line = cursor.blockNumber() + 1
        col = cursor.columnNumber() + 1
        event = broker.Event(
            'code_editor',
            'cursor_position',
            (line, col)
        )
        broker.emit(event)

    def highlight_current_line(self) -> None:
        """Add a background to the current line for visibility."""
        if self.isReadOnly():
            self.setExtraSelections([])
            return

        extraSelections = []
        selection = QtWidgets.QTextEdit.ExtraSelection()

        fmt = QtGui.QTextCharFormat()
        fmt.setBackground(QtGui.QColor(40, 40, 40))
        fmt.setProperty(QtGui.QTextFormat.Property.FullWidthSelection, True)
        selection.format = fmt

        selection.cursor = self.textCursor()
        selection.cursor.clearSelection()
        extraSelections.append(selection)
        self.setExtraSelections(extraSelections)

    # -----Code Formatting-----------------------------------------------------

    def add_line_prefix(self, prefix: str, line: int) -> None:
        """
        Adds the prefix substring to the start of a line.

        Args:
            prefix (str): The substring to append to the start of the line.
            line (int): The line number to append.
        """
        cursor = QtGui.QTextCursor(self.document().findBlockByLineNumber(line))
        self.setTextCursor(cursor)
        self.textCursor().insertText(prefix)

    def remove_line_prefix(self, prefix: str, line: int) -> None:
        """
        Removes the prefix substring from the start of a line.

        Args:
            prefix (str): The substring to remove from the start of the line.
            line (int): The line number to adjust.
        """
        cursor = QtGui.QTextCursor(self.document().findBlockByLineNumber(line))
        cursor.select(QtGui.QTextCursor.SelectionType.LineUnderCursor)
        text = cursor.selectedText()
        if text.startswith(prefix):
            cursor.removeSelectedText()
            cursor.insertText(text.split(prefix, 1)[-1])

    def _get_selection_range(self) -> tuple[int, int]:
        """
        Returns the first and last line of a continuous selection.

        Returns
            tuple[int, int]: First line number and last line number.
        """
        cursor = self.textCursor()
        start_pos = cursor.selectionStart()
        end_pos = cursor.selectionEnd()

        cursor.setPosition(start_pos)
        first_line = cursor.blockNumber()
        cursor.setPosition(end_pos)
        last_line = cursor.blockNumber()

        return first_line, last_line

    def indent(self, lines: range) -> None:
        """Indent the lines within the given range."""
        with PySide6TK.text.PlainTextUndoBlock(self):
            for i in lines:
                self.add_line_prefix(_INDENT, i)

    def unindent(self, lines: range) -> None:
        """Unindent the lines within the given range."""
        with PySide6TK.text.PlainTextUndoBlock(self):
            for i in lines:
                self.remove_line_prefix(_INDENT, i)

    def _are_lines_commented(self, lines: range) -> bool:
        """
        Check if all lines in the range are commented.

        Args:
            lines (range): Range of line numbers to check.
        Returns:
            bool: True if all lines start with comment prefix, False otherwise.
        """
        for line_num in lines:
            cursor = QtGui.QTextCursor(self.document().findBlockByLineNumber(line_num))
            cursor.select(QtGui.QTextCursor.SelectionType.LineUnderCursor)
            text = cursor.selectedText()
            if not text.lstrip(' ').startswith(_COMMENT_PREFIX.strip()):
                return False
        return True

    def comment_lines(self, lines: range) -> None:
        """Add comment prefix to lines within the given range."""
        with PySide6TK.text.PlainTextUndoBlock(self):
            for i in lines:
                self.add_line_prefix(_COMMENT_PREFIX, i)

    def uncomment_lines(self, lines: range) -> None:
        with PySide6TK.text.PlainTextUndoBlock(self):
            for i in lines:
                cursor = QtGui.QTextCursor(self.document().findBlockByLineNumber(i))
                cursor.select(QtGui.QTextCursor.SelectionType.LineUnderCursor)
                text = cursor.selectedText()

                stripped = text.lstrip(' ')
                if stripped.startswith('#'):
                    leading_spaces = len(text) - len(stripped)
                    if stripped.startswith('# '):
                        new_text = ' ' * leading_spaces + stripped[2:]
                    else:
                        new_text = ' ' * leading_spaces + stripped[1:]

                    cursor.removeSelectedText()
                    cursor.insertText(new_text)

    def toggle_comment(self) -> None:
        """Toggle comments on selected lines or current line."""
        first_line, last_line = self._get_selection_range()
        lines = range(first_line, last_line + 1)

        if self._are_lines_commented(lines):
            self.uncommented.emit(lines)
        else:
            self.commented.emit(lines)

    def wrap_selection(self, opening: str, closing: str) -> None:
        """
        Wrap the current selection with opening and closing characters.

        Args:
            opening (str): Character to insert before the selection.
            closing (str): Character to insert after the selection.
        """
        cursor = self.textCursor()
        if cursor.hasSelection():
            selected_text = cursor.selectedText()
            wrapped_text = f'{opening}{selected_text}{closing}'
            cursor.insertText(wrapped_text)
        else:
            self.insertPlainText(opening)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        """Enable shortcuts in keypress event."""
        # Toggle comment with Ctrl+/
        if event.key() == QtCore.Qt.Key.Key_Slash and event.modifiers() == QtCore.Qt.KeyboardModifier.ControlModifier:
            self.toggle_comment()
            return

        # Should text be wrapped?
        typed_char = event.text()
        if self.textCursor().hasSelection() and typed_char in _WRAPPING_PAIRS:
            self.wrap_selection(typed_char, _WRAPPING_PAIRS[typed_char])
            return

        first_line, last_line = self._get_selection_range()

        # Multi-line indent
        if event.key() == QtCore.Qt.Key.Key_Tab and last_line - first_line:
            lines = range(first_line, last_line + 1)
            self.indented.emit(lines)
            return

        # Multi-line unindent
        if event.key() == QtCore.Qt.Key.Key_Backtab:
            lines = range(first_line, last_line + 1)
            self.unindented.emit(lines)
            return

        # Tab as 4 spaces
        if event.key() == QtCore.Qt.Key.Key_Tab:
            self.insertPlainText(_INDENT)
            return

        # Enter indentation handling (preserve current indent; if line ends with ':', indent one extra level).
        if event.key() in (QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter):
            cursor = self.textCursor()
            cursor.select(QtGui.QTextCursor.SelectionType.LineUnderCursor)
            current_line = cursor.selectedText()

            # Base indent equals current line's leading spaces
            base_indent_count = len(current_line) - len(current_line.lstrip(' '))
            base_indent = ' ' * base_indent_count

            # If the logical line ends with a colon, indent to the next level
            extra = _INDENT if current_line.rstrip().endswith(':') else ''

            # Insert newline via parent, then insert computed indentation
            super(CodeEditor, self).keyPressEvent(event)
            self.insertPlainText(base_indent + extra)
            return

        super(CodeEditor, self).keyPressEvent(event)
