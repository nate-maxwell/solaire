"""
The primary tab manager in the center of the application.
All tab management is handled here.
"""


import time
from pathlib import Path
from typing import Optional
from typing import cast

from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets

from solaire.core import broker
from solaire.core import evaluator
from solaire.core import languages
from solaire.core.code_editor import CodeEditor


class DraggableTabBar(QtWidgets.QTabBar):
    """Tab bar that supports drag-and-drop reordering"""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setElideMode(QtCore.Qt.TextElideMode.ElideRight)
        self.setSelectionBehaviorOnRemove(
            QtWidgets.QTabBar.SelectionBehavior.SelectPreviousTab
        )
        self.setMovable(True)
        self._drag_start_pos: QtCore.QPoint = QtCore.QPoint()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.pos()
        super().mousePressEvent(event)


class EditorTabWidget(QtWidgets.QTabWidget):
    """Tab widget for IDE-style file editing.
    Currently hard-coded to use Solair Code Editors rather than abstract tab
    widget.
    """

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        broker.register_source('tab_manager')

        self.setTabBar(DraggableTabBar(self))
        self.setTabsClosable(True)
        self.setMovable(True)
        self.setDocumentMode(True)

        self._file_paths: dict[int, Path] = {}
        self._modified_state: dict[int, bool] = {}
        self._editor_widgets: dict[int, QtWidgets.QPlainTextEdit] = {}

        self.tabCloseRequested.connect(self._handle_tab_close)
        self.currentChanged.connect(self.on_tab_changed)
        self.tabBar().tabMoved.connect(self._handle_tab_moved)

        self._register_subscriptions()

    # -----Subscription Management---------------------------------------------

    def _register_subscriptions(self) -> None:
        """Registers all subscriptions with the broker."""

        # -----File Opened-----

        broker.register_subscriber(
            'common_event',
            'open_file',
            self._file_opened_subscription
        )
        broker.register_subscriber(
            'solaire_file_tree',
            'file_opened',
            self._file_opened_subscription
        )

        # -----Directory Changed-----

        broker.register_subscriber(
            'common_event',
            'open_folder',
            self._directory_changed_subscription
        )

        # -----File Saved-----
        broker.register_subscriber(
            'common_event',
            'save_file',
            self._save_file_subscription
        )

        # -----Save All-----
        broker.register_subscriber(
            'common_event',
            'save_all',
            self._save_all_subscription
        )

        # -----Code-----
        broker.register_subscriber(
            'SYSTEM',
            'RUN',
            self.run_code
        )

    def run_code(self, _: broker.Event) -> None:
        if not isinstance(self.currentWidget(), CodeEditor):
            return

        editor: CodeEditor = cast(CodeEditor, self.currentWidget())
        code = editor.toPlainText()

        before = time.perf_counter()
        result: Optional[str] = evaluator.execute_user_code(code)
        after = time.perf_counter()
        elapsed = after - before
        elapsed_str = f'Executed in {elapsed:.3f} seconds.'
        print('\n\n', elapsed_str)

        if result is not None:
            print(result)

    def _file_opened_subscription(self, event: broker.Event) -> None:
        """When a file open has been signaled by the broker."""
        filepath = Path(event.data)
        if not filepath.exists():
            return

        existing_index = self._find_tab_by_path(filepath)
        if existing_index >= 0:
            # File is already open, just switch to that tab
            self.setCurrentIndex(existing_index)
            self.on_tab_changed(existing_index)
            return

        highlighter = languages.generate_highlighter_from_file(filepath)
        editor = CodeEditor(self, highlighter)
        new_idx = self.open_file(filepath, editor)
        self.on_tab_changed(new_idx)

    def _directory_changed_subscription(self, _: broker.Event) -> None:
        """When a directory change has been signaled by the broker."""
        while self.count() > 0:
            self.removeTab(0)

    def _save_file_subscription(self, _: broker.Event) -> None:
        """When a file save has been signaled by the broker."""
        self.save_file()

    def _save_all_subscription(self, _: broker.Event) -> None:
        """When a save-all event has been signaled by the broker."""
        for i in range(self.count()):
            self.save_file(i)

    # -----Tab Management------------------------------------------------------

    def on_tab_changed(self, index: int) -> None:
        try:
            editor_widget = self._editor_widgets[index]
        except KeyError:
            return

        event = broker.Event(
            'tab_manager',
            'active_changed',
            editor_widget
        )
        broker.emit(event)

    def _handle_tab_moved(self, from_index: int, to_index: int) -> None:
        """Handle tab reordering by updating tracking dictionaries"""
        # Store the data from the moved tab
        moved_file_path = self._file_paths.get(from_index)
        moved_modified = self._modified_state.get(from_index)
        moved_editor = self._editor_widgets.get(from_index)

        def shift_items(idx_: int, new_idx: int) -> None:
            if new_idx in self._file_paths:
                self._file_paths[idx_] = self._file_paths[new_idx]
            elif idx_ in self._file_paths:
                del self._file_paths[idx_]

            if new_idx in self._modified_state:
                self._modified_state[idx_] = self._modified_state[new_idx]
            elif idx_ in self._modified_state:
                del self._modified_state[idx_]

            if new_idx in self._editor_widgets:
                self._editor_widgets[idx_] = self._editor_widgets[new_idx]
            elif idx_ in self._editor_widgets:
                del self._editor_widgets[idx_]

        # Determine the range and direction of the shift
        if from_index < to_index:
            # Moving right: shift items left
            for idx in range(from_index, to_index):
                next_idx = idx + 1
                shift_items(idx, next_idx)
        else:
            # Moving left: shift items right
            for idx in range(from_index, to_index, -1):
                prev_idx = idx - 1
                shift_items(idx, prev_idx)

        # Place the moved tab's data at its new position
        if moved_file_path is not None:
            self._file_paths[to_index] = moved_file_path
        if moved_modified is not None:
            self._modified_state[to_index] = moved_modified
        if moved_editor is not None:
            self._editor_widgets[to_index] = moved_editor

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.MouseButton.MiddleButton:
            pos_in_bar = self.tabBar().mapFrom(self, event.pos())
            i = self.tabBar().tabAt(pos_in_bar)
            if i != -1:
                self._handle_tab_close(i)
                event.accept()
                return
        super().mousePressEvent(event)

    def add_editor_tab(
            self,
            editor_widget: QtWidgets.QPlainTextEdit,
            file_path: Optional[Path] = None
    ) -> int:
        """
        Add a new tab with an editor widget.

        Args:
            editor_widget (QPlainTextEdit): The QPlainTextEdit or custom editor widget
            file_path (Path): Optional path to the file being edited
        Returns:
            int: Index of the newly added tab
        """
        title = 'Untitled' if file_path is None else file_path.name
        index: int = self.addTab(editor_widget, title)

        if file_path is not None:
            self._file_paths[index] = file_path

        self._editor_widgets[index] = editor_widget
        self._modified_state[index] = False

        editor_widget.document().modificationChanged.connect(
            lambda modified, widget=editor_widget: self._on_modification_changed(
                widget, modified
            )
        )
        editor_widget.modificationChanged.connect(
            lambda modified, widget=editor_widget: self._on_modification_changed(
                widget, modified
            )
        )
        editor_widget.textChanged.connect(
            lambda widget=editor_widget: self._on_text_changed(widget)
        )

        self.setCurrentIndex(index)
        return index

    def _on_text_changed(self, editor_widget: QtWidgets.QWidget) -> None:
        """Handle text changed event from an editor widget (fallback for widgets without modificationChanged)"""
        index: int = self._get_widget_index(editor_widget)
        if index >= 0:
            self._mark_modified(index)

    def _on_modification_changed(self, editor_widget: QtWidgets.QWidget,
                                 modified: bool) -> None:
        """Handle modification changed event from an editor widget"""
        index: int = self._get_widget_index(editor_widget)
        if index >= 0:
            if modified:
                self._mark_modified(index)
            else:
                self._mark_unmodified(index)

    def _get_widget_index(self, widget: QtWidgets.QWidget) -> int:
        """Find the tab index for a given widget"""
        for index, stored_widget in self._editor_widgets.items():
            if stored_widget is widget:
                return index
        return -1

    def _find_tab_by_path(self, file_path: Path) -> int:
        """
        Find the tab index for a given file path.

        Args:
            file_path: Path to search for
        Returns:
            int: Tab index if found, -1 if not found
        """
        for index, path in self._file_paths.items():
            if path == file_path:
                return index
        return -1

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

        if self.count() == 0:
            event = broker.Event('tab_manager', 'all_tabs_closed')
            broker.emit(event)

    def _mark_modified(self, index: int) -> None:
        """Mark a tab as modified (dirty)"""
        if index in self._modified_state and not self._modified_state[index]:
            self._modified_state[index] = True
            self._update_tab_title(index)

    def _mark_unmodified(self, index: int) -> None:
        """Mark a tab as unmodified (clean)"""
        if index in self._modified_state and self._modified_state[index]:
            self._modified_state[index] = False
            self._update_tab_title(index)

    def _update_tab_title(self, index: int) -> None:
        """Update tab title to reflect modified state"""
        current_title: str = self.tabText(index)

        if current_title.startswith('* '):
            current_title = current_title[2:]

        if self._modified_state.get(index, False):
            self.setTabText(index, f'* {current_title}')
        else:
            self.setTabText(index, current_title)

    def _reindex_tracking(self, removed_index: int) -> None:
        """Reindex tracking dictionaries after tab removal."""
        new_file_paths: dict[int, Path] = {}
        new_modified_state: dict[int, bool] = {}
        new_editor_widgets: dict[int, QtWidgets.QWidget] = {}

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

    # -----File Management-----------------------------------------------------

    def open_file(
            self,
            file_path: Path,
            editor_widget: CodeEditor
    ) -> int:
        """
        Open a file in a new tab.

        Args:
            file_path (Path): Path to the file to open.
            editor_widget (CodeEditor): The editor widget to use for this
                file.
        Returns:
            int: Index of the tab, or -1 if file couldn't be opened.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content: str = f.read()

            index: int = self.add_editor_tab(
                editor_widget, file_path
            )

            editor_widget.document().modificationChanged.disconnect()
            editor_widget.modificationChanged.disconnect()
            editor_widget.textChanged.disconnect()

            editor_widget.setPlainText(content)

            editor_widget.document().modificationChanged.connect(
                lambda modified, widget=editor_widget: self._on_modification_changed(
                    widget, modified
                )
            )
            editor_widget.modificationChanged.connect(
                lambda modified, widget=editor_widget: self._on_modification_changed(
                    widget, modified
                )
            )
            editor_widget.textChanged.connect(
                lambda widget=editor_widget: self._on_text_changed(widget)
            )

            editor_widget.document().setModified(False)

            self._modified_state[index] = False
            self._update_tab_title(index)

            return index

        except Exception as e:
            print(f'Error opening file {file_path.as_posix()}: {e}')
            return -1

    def save_file(self, index: Optional[int] = None) -> bool:
        """
        Save the file in the specified tab (or current tab if not specified).

        Args:
            index (int): Tab index to save (None = current tab).
        Returns:
            bool: True if saved successfully, False otherwise.
        """
        if index is None:
            index = self.currentIndex()

        if index < 0:
            return False

        file_path: Optional[Path] = self._file_paths.get(index)
        if not file_path:
            print(f'No file path associated with tab {index}')
            return False

        editor_widget: Optional[QtWidgets.QWidget] = self.widget(index)
        if not editor_widget:
            return False

        content: Optional[str] = None
        if hasattr(editor_widget, 'toPlainText'):
            content = editor_widget.toPlainText()

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            if hasattr(editor_widget, 'document') and hasattr(
                    editor_widget.document(), 'setModified'):
                editor_widget.document().setModified(False)

            self._mark_unmodified(index)

            return True

        except Exception as e:
            print(f'Error saving file {file_path.as_posix()}: {e}')
            return False

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
                self.setTabText(index, f'* {filename}')
            else:
                self.setTabText(index, filename)
