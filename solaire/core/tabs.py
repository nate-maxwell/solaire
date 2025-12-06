from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QTabWidget, QTabBar, QWidget

from solaire.core.code_editor import CodeEditor


class DraggableTabBar(QTabBar):
    """Tab bar that supports drag-and-drop reordering"""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setElideMode(Qt.TextElideMode.ElideRight)
        self.setSelectionBehaviorOnRemove(
            QTabBar.SelectionBehavior.SelectPreviousTab)
        self.setMovable(True)
        self._drag_start_pos: QPoint = QPoint()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.pos()
        super().mousePressEvent(event)


class EditorTabWidget(QTabWidget):
    """
    Tab widget for IDE-style file editing.

    Signals:
        tab_closed(int): Emitted when a tab is closed with the tab index
        file_opened(str): Emitted when a file is opened with the file path
        file_saved(str): Emitted when a file is saved with the file path
        content_modified(int, bool): Emitted when content modified state changes (index, is_modified)
    """

    tab_closed = Signal(int)
    file_opened = Signal(str)
    file_saved = Signal(str)
    content_modified = Signal(int, bool)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.setTabBar(DraggableTabBar(self))
        self.setTabsClosable(True)
        self.setMovable(True)
        self.setDocumentMode(True)

        self._file_paths: dict[int, Path] = {}
        self._modified_state: dict[int, bool] = {}
        self._editor_widgets: dict[int, QWidget] = {}

        self.tabCloseRequested.connect(self._handle_tab_close)

        self.open_file(Path(__file__), CodeEditor(parent=self))

    def add_editor_tab(
            self,
            editor_widget: QWidget,
            file_path: Optional[Path] = None,
            title: Optional[str] = None
    ) -> int:
        """
        Add a new tab with an editor widget.

        Args:
            editor_widget: The QPlainTextEdit or custom editor widget
            file_path: Optional path to the file being edited
            title: Optional tab title (defaults to "Untitled" or filename)

        Returns:
            int: Index of the newly added tab
        """
        if title is None:
            if file_path:
                title = file_path.name
            else:
                title = "Untitled"

        index: int = self.addTab(editor_widget, title)

        if file_path:
            self._file_paths[index] = file_path

        self._editor_widgets[index] = editor_widget

        self._modified_state[index] = False

        if hasattr(editor_widget, 'document') and hasattr(
                editor_widget.document(), 'modificationChanged'):
            editor_widget.document().modificationChanged.connect(
                lambda modified,
                       widget=editor_widget: self._on_modification_changed(
                    widget, modified)
            )
        elif hasattr(editor_widget, 'modificationChanged'):
            editor_widget.modificationChanged.connect(
                lambda modified,
                       widget=editor_widget: self._on_modification_changed(
                    widget, modified)
            )
        elif hasattr(editor_widget, 'textChanged'):
            editor_widget.textChanged.connect(
                lambda widget=editor_widget: self._on_text_changed(widget)
            )

        self.setCurrentIndex(index)
        return index

    def _on_text_changed(self, editor_widget: QWidget) -> None:
        """Handle text changed event from an editor widget (fallback for widgets without modificationChanged)"""
        index: int = self._get_widget_index(editor_widget)
        if index >= 0:
            self._mark_modified(index)

    def _on_modification_changed(self, editor_widget: QWidget,
                                 modified: bool) -> None:
        """Handle modification changed event from an editor widget"""
        index: int = self._get_widget_index(editor_widget)
        if index >= 0:
            if modified:
                self._mark_modified(index)
            else:
                self._mark_unmodified(index)

    def _get_widget_index(self, widget: QWidget) -> int:
        """Find the tab index for a given widget"""
        for index, stored_widget in self._editor_widgets.items():
            if stored_widget is widget:
                return index
        return -1

    def open_file(self, file_path: Path, editor_widget: QWidget) -> int:
        """
        Open a file in a new tab.

        Args:
            file_path: Path to the file to open
            editor_widget: The editor widget to use for this file

        Returns:
            int: Index of the tab, or -1 if file couldn't be opened
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content: str = f.read()

            filename: str = file_path.name
            index: int = self.add_editor_tab(editor_widget, file_path,
                                             filename)

            if hasattr(editor_widget, 'document') and hasattr(
                    editor_widget.document(), 'modificationChanged'):
                editor_widget.document().modificationChanged.disconnect()
            elif hasattr(editor_widget, 'modificationChanged'):
                editor_widget.modificationChanged.disconnect()
            elif hasattr(editor_widget, 'textChanged'):
                editor_widget.textChanged.disconnect()

            if hasattr(editor_widget, 'setPlainText'):
                editor_widget.setPlainText(content)
            elif hasattr(editor_widget, 'setText'):
                editor_widget.setText(content)

            if hasattr(editor_widget, 'document') and hasattr(
                    editor_widget.document(), 'modificationChanged'):
                editor_widget.document().modificationChanged.connect(
                    lambda modified,
                           widget=editor_widget: self._on_modification_changed(
                        widget, modified)
                )
            elif hasattr(editor_widget, 'modificationChanged'):
                editor_widget.modificationChanged.connect(
                    lambda modified,
                           widget=editor_widget: self._on_modification_changed(
                        widget, modified)
                )
            elif hasattr(editor_widget, 'textChanged'):
                editor_widget.textChanged.connect(
                    lambda widget=editor_widget: self._on_text_changed(widget)
                )

            if hasattr(editor_widget, 'document') and hasattr(
                    editor_widget.document(), 'setModified'):
                editor_widget.document().setModified(False)

            self._modified_state[index] = False
            self._update_tab_title(index)

            self.file_opened.emit(file_path.as_posix())
            return index

        except Exception as e:
            print(f"Error opening file {file_path.as_posix()}: {e}")
            return -1

    def save_file(self, index: Optional[int] = None) -> bool:
        """
        Save the file in the specified tab (or current tab if not specified).

        Args:
            index: Tab index to save (None = current tab)

        Returns:
            bool: True if saved successfully, False otherwise
        """
        if index is None:
            index = self.currentIndex()

        if index < 0:
            return False

        file_path: Optional[Path] = self._file_paths.get(index)
        if not file_path:
            print(f"No file path associated with tab {index}")
            return False

        editor_widget: Optional[QWidget] = self.widget(index)
        if not editor_widget:
            return False

        content: Optional[str] = None
        if hasattr(editor_widget, 'toPlainText'):
            content = editor_widget.toPlainText()
        elif hasattr(editor_widget, 'text'):
            content = editor_widget.text()
        else:
            print(f"Editor widget has no text getter method")
            return False

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            if hasattr(editor_widget, 'document') and hasattr(
                    editor_widget.document(), 'setModified'):
                editor_widget.document().setModified(False)

            self._mark_unmodified(index)

            self.file_saved.emit(file_path.as_posix())
            return True

        except Exception as e:
            print(f"Error saving file {file_path.as_posix()}: {e}")
            return False

    def _mark_modified(self, index: int) -> None:
        """Mark a tab as modified (dirty)"""
        if index in self._modified_state and not self._modified_state[index]:
            self._modified_state[index] = True
            self._update_tab_title(index)
            self.content_modified.emit(index, True)

    def _mark_unmodified(self, index: int) -> None:
        """Mark a tab as unmodified (clean)"""
        if index in self._modified_state and self._modified_state[index]:
            self._modified_state[index] = False
            self._update_tab_title(index)
            self.content_modified.emit(index, False)

    def _update_tab_title(self, index: int) -> None:
        """Update tab title to reflect modified state"""
        current_title: str = self.tabText(index)

        if current_title.startswith("* "):
            current_title = current_title[2:]

        if self._modified_state.get(index, False):
            self.setTabText(index, f"* {current_title}")
        else:
            self.setTabText(index, current_title)

    def _handle_tab_close(self, index: int) -> None:
        """Handle tab close request"""
        if index in self._file_paths:
            del self._file_paths[index]
        if index in self._modified_state:
            del self._modified_state[index]
        if index in self._editor_widgets:
            del self._editor_widgets[index]

        self._reindex_tracking(index)

        self.removeTab(index)
        self.tab_closed.emit(index)

    def _reindex_tracking(self, removed_index: int) -> None:
        """Reindex tracking dictionaries after tab removal"""
        new_file_paths: dict[int, Path] = {}
        new_modified_state: dict[int, bool] = {}
        new_editor_widgets: dict[int, QWidget] = {}

        for idx in sorted(self._file_paths.keys()):
            if idx < removed_index:
                new_file_paths[idx] = self._file_paths[idx]
            elif idx > removed_index:
                new_file_paths[idx - 1] = self._file_paths[idx]

        for idx in sorted(self._modified_state.keys()):
            if idx < removed_index:
                new_modified_state[idx] = self._modified_state[idx]
            elif idx > removed_index:
                new_modified_state[idx - 1] = self._modified_state[idx]

        for idx in sorted(self._editor_widgets.keys()):
            if idx < removed_index:
                new_editor_widgets[idx] = self._editor_widgets[idx]
            elif idx > removed_index:
                new_editor_widgets[idx - 1] = self._editor_widgets[idx]

        self._file_paths = new_file_paths
        self._modified_state = new_modified_state
        self._editor_widgets = new_editor_widgets

    def get_file_path(self, index: Optional[int] = None) -> Optional[Path]:
        """Get the file path for a tab"""
        if index is None:
            index = self.currentIndex()
        return self._file_paths.get(index)

    def is_modified(self, index: Optional[int] = None) -> bool:
        """Check if a tab has unsaved changes"""
        if index is None:
            index = self.currentIndex()
        return self._modified_state.get(index, False)

    def set_file_path(self, file_path: Path,
                      index: Optional[int] = None) -> None:
        """Set the file path for a tab and update its title"""
        if index is None:
            index = self.currentIndex()

        if index >= 0:
            self._file_paths[index] = file_path
            filename: str = file_path.name

            is_modified: bool = self._modified_state.get(index, False)
            if is_modified:
                self.setTabText(index, f"* {filename}")
            else:
                self.setTabText(index, filename)
