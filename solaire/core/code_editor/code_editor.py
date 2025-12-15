"""
A QPlainTextEdit wrapper with numbered lines and syntax highlighting.
This is the primary "Editing Engine" of the program.

Uses a regex syntax highlighter.
"""


from typing import Optional

import PySide6TK.text
from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets

from solaire.core import appdata
from solaire.core import broker
from solaire.core import languages
from solaire.core import timers
from solaire.core.code_editor import completion
from solaire.core.code_editor import folding
from solaire.core.code_editor import line_number
from solaire.core.code_editor.minimap import CodeMiniMap
from solaire.core.languages.python_syntax import PythonHighlighter
from solaire.core.languages.python_syntax import reload_color_scheme


optional_highlighter = Optional[languages.SyntaxHighlighter]

_COMMENT_PREFIX = '# '

_WRAPPING_PAIRS = {
    "'": "'",
    '"': '"',
    '(': ')',
    '[': ']',
    '{': '}',
    '`': '`',
}


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

        self.line_number_area = line_number.LineNumberArea(self)
        self.fold_area = folding.FoldArea(self)
        self._fold_regions: dict[int, folding.FoldRegion] = {}
        self.fold_area_width = 16
        self._last_minimap_block = 0

        # Add minimap to the right side
        self.minimap = CodeMiniMap(self, self)

        self._create_shortcut_signals()
        self._create_connections()
        self._create_subscriptions()
        self._create_fold_analyzer()
        self._create_cursor_timer()
        self._create_autosuggestions()
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

    def focusOutEvent(self, e: QtGui.QFocusEvent) -> None:
        self._completer_popup.hide()
        super().focusOutEvent(e)

    def jump_to_line(self, line_no: int) -> None:
        """Jump to a specific line in the editor."""
        cursor = self.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)
        cursor.movePosition(
            cursor.MoveOperation.Down,
            cursor.MoveMode.MoveAnchor,
            line_no - 1
        )
        self.setTextCursor(cursor)
        self.setFocus()

    def setPlainText(self, text, /) -> None:
        super().setPlainText(text)
        self.analyze_fold_regions()

    def _create_cursor_timer(self) -> None:
        prefs = appdata.Preferences().refresh
        self._cursor_timer = timers.create_bind_and_start_timer(
            self,
            prefs.cursor,
            self.cursorPositionChanged,
            self._emit_cursor_position
        )

    def _create_autosuggestions(self) -> None:
        self._completer_popup = completion.CodeCompletionPopup(self)
        if appdata.Preferences().code_preferences.enable_auto_suggest:
            self._completer_popup.activated.connect(self._insert_completion)
        self.cursorPositionChanged.connect(self._maybe_hide_popup)
        self.textChanged.connect(self._maybe_trigger_completions)

        self._completion_job_id: int = 0
        self._pending_completion_args = None

        # -----Debounce-----
        self._completion_timer = QtCore.QTimer(self)
        self._completion_timer.setSingleShot(True)
        self._completion_timer.setInterval(120)
        self._completion_timer.timeout.connect(self._kickoff_completion)

        # ---- Worker thread ----
        self._completion_bridge = completion.CompletionBridge()
        self._completion_thread = QtCore.QThread(self)
        self._completion_worker = completion.CompletionWorker()
        self._completion_worker.moveToThread(self._completion_thread)

        self._completion_bridge.request.connect(
            self._completion_worker.request,
            QtCore.Qt.ConnectionType.QueuedConnection
        )
        self._completion_worker.results.connect(self._on_completion_results)
        self._completion_thread.start()

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

    @property
    def column(self) -> int:
        """Look up and return the guide column number based on preferences."""
        prefs = appdata.Preferences()
        if not prefs.code_preferences.enable_vertical_guide:
            return 0
        else:
            return prefs.code_preferences.guide_column

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
        prefs = appdata.Preferences().refresh
        self._fold_timer = timers.create_bind_and_start_timer(
            self,
            prefs.code_fold,
            self.document().contentsChanged,
            self.analyze_fold_regions
        )

    def analyze_fold_regions(self) -> None:
        """
        Analyze document to find foldable regions.

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
                    self._fold_regions[start_block] = folding.FoldRegion(
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
                                self._fold_regions[open_block] = folding.FoldRegion(
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
        block_number = block.blockNumber()
        block_geo = self.blockBoundingGeometry(block)
        top = block_geo.translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        height = self.fontMetrics().height()
        while block.isValid() and (top <= event.rect().bottom()):
            if block.isVisible() and (bottom >= event.rect().top()):
                number = str(block_number + 1)
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
            block_number += 1

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

        extra_selections = []
        selection = QtWidgets.QTextEdit.ExtraSelection()

        fmt = QtGui.QTextCharFormat()
        fmt.setBackground(QtGui.QColor(40, 40, 40))
        fmt.setProperty(QtGui.QTextFormat.Property.FullWidthSelection, True)
        selection.format = fmt

        selection.cursor = self.textCursor()
        selection.cursor.clearSelection()
        extra_selections.append(selection)
        self.setExtraSelections(extra_selections)

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

    @property
    def _indent(self) -> str:
        """Look up and return the appropriate tab string based on preferences."""
        prefs = appdata.Preferences()
        if prefs.code_preferences.tab_type == appdata.TAB_TYPE_SPACE:
            return ' ' * prefs.code_preferences.tab_space_width
        elif prefs.code_preferences.tab_type == appdata.TAB_TYPE_TAB:
            return '\t'
        else:
            raise appdata.AppdataError('Unknown tab type from preferences!')

    def indent(self, lines: range) -> None:
        """Indent the lines within the given range."""
        with PySide6TK.text.PlainTextUndoBlock(self):
            for i in lines:
                self.add_line_prefix(self._indent, i)

    def unindent(self, lines: range) -> None:
        """Unindent the lines within the given range."""
        with PySide6TK.text.PlainTextUndoBlock(self):
            for i in lines:
                self.remove_line_prefix(self._indent, i)

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
        """Enable shortcuts in keypress event + code completion handling."""
        if self._completer_popup.isVisible():
            mods = event.modifiers()
            key = event.key()

            # Give Shift+navigation back to the editor (even with Ctrl held)
            shift_nav_keys = (
                QtCore.Qt.Key.Key_Left,
                QtCore.Qt.Key.Key_Right,
                QtCore.Qt.Key.Key_Up,
                QtCore.Qt.Key.Key_Down,
                QtCore.Qt.Key.Key_Home,
                QtCore.Qt.Key.Key_End,
                QtCore.Qt.Key.Key_PageUp,
                QtCore.Qt.Key.Key_PageDown
            )
            if (
                    (mods & QtCore.Qt.KeyboardModifier.ShiftModifier)
                    and key in shift_nav_keys
            ):
                return super().keyPressEvent(event)

            # Popup navigation
            if key == QtCore.Qt.Key.Key_Down:
                self._completer_popup.select_next()
                return None

            if key == QtCore.Qt.Key.Key_Up:
                self._completer_popup.select_prev()
                return None

            # TAB accepts the completion
            if key == QtCore.Qt.Key.Key_Tab:
                self._insert_completion(self._completer_popup.current_text())
                return None

            # Enter adds newline, does not accept suggestion - Only tab does.
            if key in (QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter):
                self._completer_popup.hide()
                return super().keyPressEvent(event)

            if key == QtCore.Qt.Key.Key_Escape:
                self._completer_popup.hide()
                return None

        # Toggle comment with Ctrl+/
        if (
                event.key() == QtCore.Qt.Key.Key_Slash
                and event.modifiers() == QtCore.Qt.KeyboardModifier.ControlModifier
        ):
            self.toggle_comment()
            self._maybe_trigger_completions()
            return None

        # Wrapping selection
        typed_char = event.text()
        if self.textCursor().hasSelection() and typed_char in _WRAPPING_PAIRS:
            self.wrap_selection(typed_char, _WRAPPING_PAIRS[typed_char])
            self._maybe_trigger_completions()
            return None

        first_line, last_line = self._get_selection_range()

        # Multi-line indent
        if event.key() == QtCore.Qt.Key.Key_Tab and last_line - first_line:
            lines = range(first_line, last_line + 1)
            self.indented.emit(lines)
            self._completer_popup.hide()
            return None

        # Multi-line unindent
        if event.key() == QtCore.Qt.Key.Key_Backtab:
            lines = range(first_line, last_line + 1)
            self.unindented.emit(lines)
            self._completer_popup.hide()
            return None

        # Smart single-line indent
        if event.key() == QtCore.Qt.Key.Key_Tab:
            self.insertPlainText(self._indent)
            self._completer_popup.hide()
            return None

        # Enter indentation handling (preserve current indent; colon adds level)
        if event.key() in (QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter):
            cursor = self.textCursor()
            cursor.select(QtGui.QTextCursor.SelectionType.LineUnderCursor)
            cur_line = cursor.selectedText()

            base_indent_count = len(cur_line) - len(cur_line.lstrip(' '))
            base_indent = ' ' * base_indent_count
            extra = self._indent if cur_line.rstrip().endswith(':') else ''

            super(CodeEditor, self).keyPressEvent(event)
            self.insertPlainText(base_indent + extra)
            self._completer_popup.hide()
            return None

        super(CodeEditor, self).keyPressEvent(event)
        self._maybe_trigger_completions()
        return None

    # -----Completion Suggestion------------------------------------------------

    def _current_prefix(self) -> str:
        """Return the [A-Za-z0-9_]+ prefix immediately left of the caret, safely."""
        cur = self.textCursor()
        line_text = cur.block().text()  # robust: never shorter than selection quirks
        col = cur.columnNumber()  # 0-based column within the line

        if col <= 0 or not line_text:
            return ''

        i = col - 1
        # Walk left while identifier characters
        while i >= 0:
            ch = \
            line_text[
                i]
            if ch.isalnum() or ch == '_':
                i -= 1
                continue
            break

        return line_text[
            i + 1:col]

    def _document_text_and_cursor(self) -> tuple[str, int, int]:
        """Return (full_text, 1-based line, 1-based col) for jedi."""
        text = self.document().toPlainText()
        cur = self.textCursor()
        line = cur.blockNumber() + 1
        col = cur.columnNumber()
        return text, line, col

    def _popup_position(self) -> tuple[QtCore.QPoint, int]:
        """Return (global_point_below_caret, width_px) for popup."""
        r = self.cursorRect()
        below = QtCore.QPoint(r.left(), r.bottom())
        global_pt = self.viewport().mapToGlobal(below)
        # Reasonable width: 30 'M' chars
        width_px = int(QtGui.QFontMetrics(self.font()).horizontalAdvance('M') * 30)
        return global_pt, width_px

    @staticmethod
    def _dedupe_ordered(seq: list[str]) -> list[str]:
        seen = set()
        out = []
        for s in seq:
            if s not in seen:
                seen.add(s)
                out.append(s)
        return out

    def _maybe_trigger_completions(self) -> None:
        if self.isReadOnly():
            self._completer_popup.hide()
            return

        prefix = self._current_prefix()
        ch_left = self._char_left_of_caret()
        if not prefix and ch_left != '.':
            self._completer_popup.hide()
            return

        # Prepare the latest request, but don't compute yet — debounce
        try:
            text, line, col = self._document_text_and_cursor()
            self._pending_completion_args = (text, line, col)
            self._completion_job_id += 1  # unique id for this intent
            self._completion_timer.start()  # (re)start debounce
        except Exception:
            self._completer_popup.hide()

    def _char_left_of_caret(self) -> str:
        cur = self.textCursor()
        line_text = cur.block().text()
        col = cur.columnNumber()
        if col <= 0 or not line_text:
            return ''
        return line_text[col - 1]

    def _kickoff_completion(self) -> None:
        if not self._pending_completion_args:
            return
        text, line, col = self._pending_completion_args
        job_id = self._completion_job_id

        # Queue the job to the worker thread
        self._completion_bridge.request.emit(text, line, col, job_id)

    @QtCore.Slot(int, list)
    def _on_completion_results(self, job_id: int, names: list) -> None:
        # Drop stale results (user kept typing, new job id superseded)
        if job_id != self._completion_job_id:
            return

        if not names:
            self._completer_popup.hide()
            return

        # Show quickly; keep editor focused for smooth typing
        gp, w = self._popup_position()
        if appdata.Preferences().code_preferences.enable_auto_suggest:
            self._completer_popup.show_completions(names, gp, w)

    def _maybe_hide_popup(self) -> None:
        # Hide when caret moves to a different line or popup would overlap oddly
        if not self._completer_popup.isVisible():
            return
        # Reposition to follow the caret
        gp, w = self._popup_position()
        self._completer_popup.move(gp)

    def _insert_completion(self, chosen: str) -> None:
        """
        Insert only the remaining text after the current prefix.
        Handles function call snippets like 'func(param)' by inserting name first.
        """
        # If the item looks like 'name(params...)', only complete 'name' here.
        name_only = chosen.split('(', 1)[0] if '(' in chosen else chosen

        prefix = self._current_prefix()
        remainder = name_only[len(prefix):] if name_only.startswith(prefix) else name_only

        if not remainder:
            self._completer_popup.hide()
            return

        with PySide6TK.text.PlainTextUndoBlock(self):
            self.insertPlainText(remainder)

        self._completer_popup.hide()
