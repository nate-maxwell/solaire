import sys
from typing import Optional
from typing import TextIO

from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets


class _QtStream(QtCore.QObject):
    """Qt-friendly text sink that emits written chunks via a signal.

    Args:
        is_error: If True, mark chunks as error (stderr).
        tee: Optional secondary stream to also write to (e.g., original sys.stdout/sys.stderr).
    """
    text_emitted = QtCore.Signal(str, bool)

    def __init__(
            self,
            is_error: bool = False,
            tee: Optional[TextIO] = None
    ) -> None:
        super().__init__()
        self.is_error = is_error
        self._tee = tee

    def write(self, s: str) -> int:
        if not isinstance(s, str):
            s = str(s)

        if self._tee is not None:
            try:
                self._tee.write(s)
            except Exception:
                pass

        self.text_emitted.emit(s, self.is_error)
        return len(s)

    def flush(self) -> None:
        if self._tee is not None:
            try:
                self._tee.flush()
            except Exception:
                pass


class TerminalWidget(QtWidgets.QTextEdit):
    """PySide6 terminal showing stdout/stderr in white/red.

    Args:
        parent: Optional parent widget.
        install_as_sys: If True, replace sys.stdout/sys.stderr immediately.
        wrap_lines: If True, enable line wrapping in the view.
        tee_to_original: If True, also mirror output to original sys streams.
    """

    def __init__(
        self,
        parent: Optional[QtWidgets.QWidget] = None,
        *,
        install_as_sys: bool = True,
        wrap_lines: bool = False,
        tee_to_original: bool = False,
    ) -> None:
        super().__init__(parent)

        self.setReadOnly(True)
        self.setAcceptRichText(False)
        self.setUndoRedoEnabled(False)
        self.setLineWrapMode(
            QtWidgets.QTextEdit.LineWrapMode.WidgetWidth
            if wrap_lines
            else QtWidgets.QTextEdit.LineWrapMode.NoWrap
        )
        self.setStyleSheet(
            'QTextEdit { background-color: #202020; color: #E0E0E0; }'
        )

        fixed = QtGui.QFontDatabase.systemFont(
            QtGui.QFontDatabase.SystemFont.FixedFont
        )
        fixed.setPointSize(10)
        self.setFont(fixed)

        pal = self.palette()
        pal.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor(16, 16, 16))
        pal.setColor(QtGui.QPalette.ColorRole.Text, QtGui.QColor(240, 240, 240))
        self.setPalette(pal)

        # Keep originals so we can restore
        self._old_stdout: Optional[TextIO] = sys.stdout
        self._old_stderr: Optional[TextIO] = sys.stderr

        self.stdout_stream = _QtStream(
            is_error=False, tee=self._old_stdout if tee_to_original else None
        )
        self.stderr_stream = _QtStream(
            is_error=True, tee=self._old_stderr if tee_to_original else None
        )

        self.stdout_stream.text_emitted.connect(
            self._append_text, QtCore.Qt.ConnectionType.QueuedConnection
        )
        self.stderr_stream.text_emitted.connect(
            self._append_text, QtCore.Qt.ConnectionType.QueuedConnection
        )

        if install_as_sys:
            self.install()

    def install(self) -> None:
        """Replace sys.stdout/sys.stderr with the terminal streams."""
        sys.stdout = self.stdout_stream
        sys.stderr = self.stderr_stream

    def uninstall(self) -> None:
        """Restore original sys.stdout/sys.stderr."""
        if self._old_stdout is not None:
            sys.stdout = self._old_stdout
        if self._old_stderr is not None:
            sys.stderr = self._old_stderr

    def write(self, text: str, *, is_error: bool = False) -> None:
        """Programmatically write text to the terminal."""
        self._append_text(text, is_error)

    @QtCore.Slot(str, bool)
    def _append_text(self, text: str, is_error: bool) -> None:
        sb = self.verticalScrollBar()
        at_bottom = sb.value() >= (sb.maximum() - 2)

        cursor = self.textCursor()
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)

        fmt = QtGui.QTextCharFormat()
        if is_error:
            fmt.setForeground(QtGui.QBrush(QtGui.QColor(220, 80, 80)))
        else:
            fmt.setForeground(QtGui.QBrush(QtGui.QColor(240, 240, 240)))
        cursor.setCharFormat(fmt)
        cursor.insertText(text)

        if at_bottom:
            self.moveCursor(QtGui.QTextCursor.MoveOperation.End)
            sb.setValue(sb.maximum())

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """Ensures we put sys streams back."""
        self.uninstall()
        super().closeEvent(event)

    def contextMenuEvent(self, event: QtGui.QContextMenuEvent) -> None:
        menu = self.createStandardContextMenu()
        menu.addSeparator()
        act_clear = menu.addAction('Clear')

        chosen = menu.exec(event.globalPos())
        if chosen is act_clear:
            self.clear()
