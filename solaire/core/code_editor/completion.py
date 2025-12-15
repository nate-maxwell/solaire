"""
Jedi-based code suggestion widget.
"""


import jedi
from PySide6 import QtCore
from PySide6 import QtWidgets


class CodeCompletionPopup(QtWidgets.QFrame):
    """Lightweight popup for code completions."""
    activated = QtCore.Signal(str)  # emits the chosen completion text

    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent, QtCore.Qt.WindowType.ToolTip)
        self.setWindowFlag(QtCore.Qt.WindowType.FramelessWindowHint, True)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)

        self.setObjectName('CodeCompletionPopup')
        self.setFrameStyle(
            QtWidgets.QFrame.Shape.Box |
            QtWidgets.QFrame.Shadow.Plain
        )

        self._list = QtWidgets.QListWidget(self)
        self._list.setUniformItemSizes(True)
        self._list.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._list.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection
        )

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._list)

        self._list.itemActivated.connect(self._on_item_activated)

    def show_completions(
            self,
            items: list[str],
            at_global_pos: QtCore.QPoint,
            width_px: int
    ) -> None:
        self._list.clear()
        for s in items:
            self._list.addItem(s)

        if not items:
            self.hide()
            return

        self._list.clearSelection()  # Start with NO selection by default
        self._list.setCurrentRow(-1)

        max_rows = min(12, self._list.count())
        row_height = self._list.sizeHintForRow(0) if self._list.count() else 18
        max_height = (max_rows * row_height) + 6
        self.resize(width_px, max_height)
        self.move(at_global_pos)
        self.show()

        # keep typing in the editor
        p = self.parentWidget()
        if p is not None:
            p.setFocus(QtCore.Qt.FocusReason.OtherFocusReason)

    def current_text(self) -> str:
        it = self._list.currentItem()
        return '' if it is None else it.text()

    def select_next(self) -> None:
        count = self._list.count()
        if count == 0:
            return
        cur = self._list.currentRow()
        row = 0 if cur < 0 else (cur + 1) % count
        self._list.setCurrentRow(row)

    def select_prev(self) -> None:
        count = self._list.count()
        if count == 0:
            return
        cur = self._list.currentRow()
        row = (count - 1) if cur < 0 else (cur - 1) % count
        self._list.setCurrentRow(row)

    def _on_item_activated(self, item: QtWidgets.QListWidgetItem) -> None:
        self.activated.emit(item.text())
        self.hide()


class CompletionWorker(QtCore.QObject):
    results = QtCore.Signal(int, list)  # (job_id, names)

    @QtCore.Slot(str, int, int, int)
    def request(self, text: str, line: int, col: int, job_id: int) -> None:
        try:
            script = jedi.Script(code=text)
            comps = script.complete(line=line, column=col)
            # Keep it light: names only, cap the list
            names = [c.name for c in comps[:64]]
        except Exception:
            names = []
        self.results.emit(job_id, names)


class CompletionBridge(QtCore.QObject):
    """
    A Qt signal relay object whose only job is to safely deliver completion
    requests from the GUI thread into a worker thread.
    Specifically for Jedi code completion.
    """
    # code, line, col, job_id
    request = QtCore.Signal(str, int, int, int)
