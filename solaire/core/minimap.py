"""
# Code Mini Map

Description:

    A VSCode-like minimap widget for code editors that derive from
    QPlainTextEdit. Optimized for performance with caching and reduced
    paint operations.
"""


from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets


class CodeMiniMap(QtWidgets.QWidget):
    """
    A VSCode-style minimap widget for QPlainTextEdit-based code editors.

    Displays a miniaturized, scrollable overview of the entire document
    with syntax highlighting colors. The minimap shows a viewport indicator
    rectangle representing the currently visible portion of the editor, and
    allows navigation by clicking or dragging within the minimap.

    The minimap automatically centers around the editor's current viewport
    and scrolls as you navigate through the document, similar to VSCode's
    behavior.

    Attributes:
        editor (QtWidgets.QPlainTextEdit): The text editor to create a
            minimap for.
        line_height (int): Height in pixels for each line in the minimap.
            Default: 2.
        char_width (int): Width in pixels for each character block.
            Default: 1.
        scroll_sensitivity (float): Multiplier for scroll speed when
            dragging. Values > 1.0 increase sensitivity, < 1.0 decrease it.
            Default: 1.0.

    Args:
        editor (QtWidgets.QPlainTextEdit): The code editor to attach the
            minimap to.
        parent (QtWidgets.QWidget | None): Optional parent widget.

    Example:
        >>> editor = CodeEditor()
        >>> minimap = CodeMiniMap(editor)
        >>> minimap.color_brightness = 0.4  # Darker colors
        >>> minimap.scroll_sensitivity = 1.5  # More sensitive scrolling
    """

    def __init__(
        self,
        editor: QtWidgets.QPlainTextEdit,
        parent: QtWidgets.QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.editor = editor
        self.text_scale = 0.15
        self.visible_rect = QtCore.QRect()
        self.line_height = 2
        self.char_width = 1
        self.scroll_sensitivity = 1.0
        self._color_brightness = 0.6

        self._color_cache = {}  # char pos : color mappings
        self._cached_lines = []
        self._cached_visible_blocks = []

        self._bg_color = QtGui.QColor(30, 30, 30)
        self._fallback_color = self._adjust_color_brightness(
            QtGui.QColor(212, 212, 212)
        )

        self.editor.textChanged.connect(self._on_text_changed)
        if hasattr(editor, 'foldingChanged'):
            editor.foldingChanged.connect(self._on_folding_changed)

        self.setFixedWidth(120)
        self.setMouseTracking(True)

    @property
    def color_brightness(self) -> float:
        return self._color_brightness

    @color_brightness.setter
    def color_brightness(self, value: float) -> None:
        if self._color_brightness == value:
            return
        self._color_brightness = value
        self._color_cache.clear()
        self._fallback_color = self._adjust_color_brightness(QtGui.QColor(212, 212, 212))
        self.update()

    def _on_text_changed(self) -> None:
        """Handle text changes - invalidate caches"""
        self._color_cache.clear()
        self._cached_lines = []
        self._cached_visible_blocks = None
        self.update()

    def _on_folding_changed(self) -> None:
        """Handle folding changes - invalidate visible blocks cache"""
        self._cached_visible_blocks = None
        self.update()

    def _get_visible_blocks(self) -> list[int]:
        """Get list of visible (non-folded) block numbers - cached"""
        if self._cached_visible_blocks is not None:
            return self._cached_visible_blocks

        visible = []
        block = self.editor.document().firstBlock()

        while block.isValid():
            if block.isVisible():
                visible.append(block.blockNumber())
            block = block.next()

        self._cached_visible_blocks = visible
        return visible

    @staticmethod
    def _find_block_index_in_visible(
            block_num: int,
            visible_blocks: list[int]
    ) -> int:
        """Find the index of a block number in the visible blocks list"""
        try:
            return visible_blocks.index(block_num)
        except ValueError:
            # If exact block not found, find the closest visible block
            for i, vb in enumerate(visible_blocks):
                if vb >= block_num:
                    return i
            return len(visible_blocks) - 1 if visible_blocks else -1

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, False)
        painter.fillRect(self.rect(), self._bg_color)

        if not self._cached_lines:
            self._cached_lines = self.editor.toPlainText().split('\n')

        lines = self._cached_lines
        minimap_height = self.height()

        # Get visible blocks
        visible_blocks = self._get_visible_blocks()
        if not visible_blocks:
            return

        # Find center line among visible blocks
        first_visible = self.editor.firstVisibleBlock().blockNumber()
        center_index = self._find_block_index_in_visible(
            first_visible,
            visible_blocks
        )
        if center_index == -1:
            center_index = 0

        lines_in_minimap = minimap_height // self.line_height
        center_pos = center_index - lines_in_minimap
        scroll_offset = max(
            0,
            min(center_pos // 2, len(visible_blocks) - lines_in_minimap)
        )

        start_idx = max(0, int(scroll_offset))
        end_idx = min(len(visible_blocks), start_idx + lines_in_minimap + 1)

        # Pre-allocate rect for reuse
        rect = QtCore.QRect(0, 0, self.char_width, self.line_height)
        max_width = self.width() - 5

        y_offset = 0
        for idx in range(start_idx, end_idx):
            if idx >= len(visible_blocks) or y_offset >= minimap_height:
                break

            block_num = visible_blocks[idx]
            if block_num >= len(lines):
                continue

            line = lines[block_num]
            left_margin = 5
            char_position = sum(len(lines[i]) + 1 for i in range(block_num))

            for j, char in enumerate(line):
                if left_margin > max_width:
                    break

                if char not in (' ', '\t'):
                    color = self._get_char_color_cached(char_position + j)
                    rect.moveTo(left_margin, y_offset)
                    painter.fillRect(rect, color)

                left_margin += self.char_width

            y_offset += self.line_height

        self._draw_viewport_indicator(painter, len(visible_blocks), scroll_offset)

    def _get_char_color_cached(self, position: int) -> QtGui.QColor:
        """Get color with caching to avoid repeated format lookups"""
        if position in self._color_cache:
            return self._color_cache[position]

        color = self._get_char_color(position)

        # Limit cache size to prevent memory issues
        if len(self._color_cache) > 10000:
            self._color_cache.clear()

        self._color_cache[position] = color
        return color

    def _get_char_color(self, position: int) -> QtGui.QColor:
        """Get color from editor's text format at position"""
        doc = self.editor.document()

        if position >= doc.characterCount():
            return self._fallback_color

        block = doc.findBlock(position)
        if not block.isValid():
            return self._fallback_color

        block_position = position - block.position()

        # Get formats for this block
        layout = block.layout()
        if layout is None:
            return self._fallback_color

        formats = layout.formats()

        # Find the format that applies to our position
        for fmt_range in formats:
            if fmt_range.start <= block_position < fmt_range.start + fmt_range.length:
                color = fmt_range.format.foreground().color()
                if color.isValid():
                    return self._adjust_color_brightness(color)

        return self._fallback_color

    def _adjust_color_brightness(self, color: QtGui.QColor) -> QtGui.QColor:
        """Adjust color brightness for minimap display"""
        h, s, v, a = color.getHsv()
        v = int(v * self._color_brightness)
        adjusted = QtGui.QColor()
        adjusted.setHsv(h, s, v, a)
        return adjusted

    def _draw_viewport_indicator(
            self,
            painter: QtGui.QPainter,
            total_visible_lines: int,
            scroll_offset: float = 0
    ) -> None:
        """Draw rectangle showing visible portion of editor"""
        if total_visible_lines == 0:
            return

        first_visible = self.editor.firstVisibleBlock().blockNumber()
        viewport_height = self.editor.viewport().height()
        block_height = self.editor.fontMetrics().height()
        visible_blocks = viewport_height // block_height + 1

        visible_block_list = self._get_visible_blocks()
        first_visible_index = self._find_block_index_in_visible(
            first_visible,
            visible_block_list
        )

        # Calculate position in minimap coordinates
        rect_y = (first_visible_index - scroll_offset) * self.line_height
        rect_height = visible_blocks * self.line_height

        # Clamp to minimap bounds
        rect_y = max(0, min(int(rect_y), self.height() - int(rect_height)))
        rect_height = min(int(rect_height), self.height())

        # View rect overlay
        painter.setPen(QtGui.QPen(QtGui.QColor(100, 100, 100), 1))
        painter.setBrush(QtGui.QColor(255, 255, 255, 30))
        painter.drawRect(0, rect_y, self.width(), rect_height)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        """Handle click to jump to position"""
        self._scroll_to_position(event.position().y())

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        """Handle drag to scroll"""
        if event.buttons() & QtCore.Qt.MouseButton.LeftButton:
            self._scroll_to_position(event.position().y())

    def _scroll_to_position(self, y: float) -> None:
        """Scroll editor to clicked position in minimap"""
        visible_blocks = self._get_visible_blocks()
        if not visible_blocks:
            return

        first_visible = self.editor.firstVisibleBlock().blockNumber()
        viewport_height = self.editor.viewport().height()
        block_height = self.editor.fontMetrics().height()
        visible_blocks_count = viewport_height // block_height + 1

        center_index = self._find_block_index_in_visible(
            first_visible,
            visible_blocks
        )
        lines_in_minimap = self.height() // self.line_height
        center_pos = center_index - lines_in_minimap
        scroll_offset = max(
            0,
            min(center_pos // 2, len(visible_blocks) - lines_in_minimap)
        )

        # Calculate clicked visible block index
        cur_pos = int((y / self.line_height) * self.scroll_sensitivity)
        clicked_idx = max(
            0,
            min(cur_pos + int(scroll_offset), len(visible_blocks) - 1)
        )
        clicked_block_num = visible_blocks[clicked_idx]

        # Center viewport on that block
        centered_scroll_line = clicked_block_num - visible_blocks_count // 2

        scrollbar = self.editor.verticalScrollBar()
        centered_scroll_line = max(
            scrollbar.minimum(),
            min(centered_scroll_line, scrollbar.maximum())
        )
        scrollbar.setValue(int(centered_scroll_line))

        self.update()

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        """Forward scroll events to editor"""
        self.editor.wheelEvent(event)
