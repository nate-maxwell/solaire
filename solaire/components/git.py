"""
Qt-based Git UI widget for basic repository operations.

This module provides a QWidget that exposes common Git commands
(commit, push, pull, status) and executes them asynchronously
using a worker thread to avoid blocking the UI.
"""


import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from typing import Sequence

from PySide6 import QtCore
from PySide6 import QtWidgets
from PySide6TK import QtWrappers

from solaire.core import broker


@dataclass(frozen=True)
class GitCommandResult(object):
    command: str
    """Full command string that was executed."""
    return_code: int
    """Process exit code."""
    stdout: str
    """Standard output captured from the command."""
    stderr: str
    """Standard error captured from the command."""


class GitWidget(QtWidgets.QWidget):
    """
    Widget providing basic Git operations for a repository.

    Attributes:
        result_ready (QtCore.Signal): Emitted when a Git command completes.
    Args:
        repo_path (Path): Path to the Git repository.
        parent (Optional[QtWidgets.QWidget]): Optional Qt parent widget.
    """

    result_ready = QtCore.Signal(object)

    def __init__(
        self,
        repo_path: Path,
        visible: bool = False,
        parent: Optional[QtWidgets.QWidget] = None
    ) -> None:
        super().__init__(parent)
        self._repo_path: Path = repo_path
        self.setObjectName('GitWidget')
        self.setVisible(visible)

        # Cached branch/status header from `git status --porcelain -b`.
        self._status_header: str = ''

        self._runner: _GitCommandRunner = _GitCommandRunner(self)
        self._create_widgets()
        self._create_layout()
        self._create_connections()
        self._create_subscriptions()

        self._set_busy(False)
        self._refresh_status()

    def _create_widgets(self) -> None:
        """Create child widgets used by the Git widget."""
        self._status_label = QtWidgets.QLineEdit(self)
        self._status_label.setText('')
        self._status_label.setReadOnly(True)

        self._message_line_edit = QtWidgets.QLineEdit(self)
        self._message_line_edit.setPlaceholderText('Commit message (required)')

        self._commit_button = QtWidgets.QPushButton(self)
        self._commit_button.setText('Commit')
        self._push_button = QtWidgets.QPushButton(self)
        self._push_button.setText('Push')
        self._pull_button = QtWidgets.QPushButton(self)
        self._pull_button.setText('Pull')

        self._add_selected_button = QtWidgets.QPushButton(self)
        self._add_selected_button.setText('Add Selected')
        self._unstage_selected_button = QtWidgets.QPushButton(self)
        self._unstage_selected_button.setText('Unstage Selected')

        self._progress = QtWidgets.QProgressBar(self)
        self._progress.setRange(0, 0)
        self._progress.setVisible(False)

        self._files_list = QtWidgets.QListWidget(self)
        self._files_list.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self._files_list.setUniformItemSizes(True)

    def _create_layout(self) -> None:
        """Assemble the widget layout."""
        header = QtWidgets.QVBoxLayout()
        header.addWidget(self._status_label)

        buttons_row = QtWidgets.QHBoxLayout()
        buttons_row.addWidget(self._commit_button)
        buttons_row.addWidget(self._push_button)
        buttons_row.addWidget(self._pull_button)

        stage_row = QtWidgets.QHBoxLayout()
        stage_row.addWidget(self._add_selected_button)
        stage_row.addWidget(self._unstage_selected_button)

        root = QtWidgets.QVBoxLayout(self)
        root.addLayout(header)
        root.addWidget(self._message_line_edit)
        root.addLayout(buttons_row)
        root.addWidget(QtWrappers.HorizontalLine())
        root.addLayout(stage_row)
        root.addWidget(self._progress)
        root.addWidget(self._files_list, 1)

        self.setLayout(root)

    def _create_connections(self) -> None:
        """Connect signals to their respective slots."""
        self._commit_button.clicked.connect(self._on_commit_clicked)
        self._push_button.clicked.connect(self._on_push_clicked)
        self._pull_button.clicked.connect(self._on_pull_clicked)
        self._add_selected_button.clicked.connect(self._on_add_selected_clicked)
        self._unstage_selected_button.clicked.connect(
            self._on_unstage_selected_clicked
        )

        self._runner.result_ready.connect(self._on_result_ready)
        self.result_ready.connect(self._append_result_to_output)

    def _create_subscriptions(self) -> None:
        """Create subscriptions within core system."""
        broker.register_subscriber(
            'common_event',
            'open_folder',
            self._on_directory_changed
        )

    def _on_directory_changed(self, event: broker.Event) -> None:
        """Subscribable wrapper to set_repo_path(), clearing current output."""
        self._files_list.clear()
        self._status_label.setText('')
        self.set_repo_path(event.data)

    def set_repo_path(self, repo_path: Path) -> None:
        """
        Update the active Git repository path.

        Args:
            repo_path (Path): New repository path.
        """
        self._repo_path = repo_path
        self._refresh_status()

    def _on_commit_clicked(self) -> None:
        """Handle Commit button click."""
        message = self._message_line_edit.text().strip()
        if not message:
            QtWidgets.QMessageBox.warning(
                self, 'Commit', 'Commit message is required.'
            )
            return
        self._run_git(['commit', '-m', message])

    def _on_push_clicked(self) -> None:
        """Handle Push button click."""
        self._run_git(['push'])

    def _on_pull_clicked(self) -> None:
        """Handle Pull button click."""
        self._run_git(['pull'])

    def _refresh_status(self) -> None:
        """Run a Git status command."""
        self._run_git(['status', '--porcelain', '-b'])

    def _on_add_selected_clicked(self) -> None:
        """Stage (git add) the currently selected files."""
        paths: list[str] = []
        for item in self._files_list.selectedItems():
            path = item.data(QtCore.Qt.ItemDataRole.UserRole)
            if isinstance(path, str) and path:
                paths.append(path)

        if not paths:
            self._status_label.setText('No files selected to add.')
            return

        self._run_git(['add', '--', *paths])

    def _on_unstage_selected_clicked(self) -> None:
        """Unstage (git restore --staged) the currently selected files."""
        paths: list[str] = []
        for item in self._files_list.selectedItems():
            path = item.data(QtCore.Qt.ItemDataRole.UserRole)
            if isinstance(path, str) and path:
                paths.append(path)

        if not paths:
            self._status_label.setText('No files selected to unstage.')
            return

        self._run_git(['restore', '--staged', '--', *paths])

    def _run_git(self, args: Sequence[str]) -> None:
        """
        Execute a Git command via the command runner.

        Args:
            args (Sequence[str]): Git command arguments (excluding 'git').
        """
        if not self._repo_path.exists():
            QtWidgets.QMessageBox.critical(
                self,
                'Git',
                f'Repo path does not exist:\n{self._repo_path.as_posix()}',
            )
            return

        if self._runner.is_running:
            self._status_label.setText('A git command is already running.')
            return

        self._set_busy(True)
        self._status_label.setText('')
        self._runner.run(self._repo_path, args)

    def _set_busy(self, busy: bool) -> None:
        """
        Enable or disable UI elements during command execution.

        Args:
            busy (bool): Whether a Git command is currently running.
        """
        self._progress.setVisible(busy)

        self._commit_button.setEnabled(not busy)
        self._push_button.setEnabled(not busy)
        self._pull_button.setEnabled(not busy)
        self._message_line_edit.setEnabled(not busy)
        self._add_selected_button.setEnabled(not busy)
        self._unstage_selected_button.setEnabled(not busy)

    def _on_result_ready(self, result: GitCommandResult) -> None:
        """
        Handle completion of a Git command.

        Args:
            result (GitCommandResult): Result of the completed Git command.
        """
        self._set_busy(False)
        self.result_ready.emit(result)

    def _append_result_to_output(self, result: GitCommandResult) -> None:
        """
        Handle command completion.

        For `git status --porcelain -b`, the file list is rebuilt and each item
        is tagged with a marker:

        - `[+]` : staged (index status is not a space)
        - `[ ]` : not staged

        Args:
            result (GitCommandResult): Result of the completed Git command.
        """

        # Surface errors and a small status summary.
        if result.return_code != 0:
            msg = result.stderr.strip() or f'Git exited with {result.return_code}.'
            self._status_label.setText(msg)
        else:
            self._status_label.setText('OK')

        if ' status --porcelain' in result.command:
            self._populate_status_list(result.stdout)
            return

        # Most operations that change state should refresh status.
        self._refresh_status()

    def _populate_status_list(self, stdout: str) -> None:
        """
        Populate the file list from `git status --porcelain -b` output.

        Args:
            stdout (str): Raw stdout from the porcelain status command.
        """
        self._files_list.blockSignals(True)
        try:
            self._files_list.clear()

            header, entries = self._parse_porcelain_status(stdout)
            self._status_header = header
            if header:
                self._status_label.setText(header)

            for entry in entries:
                item = QtWidgets.QListWidgetItem(self._format_file_item_text(entry))
                item.setData(QtCore.Qt.ItemDataRole.UserRole, entry['path'])
                item.setData(QtCore.Qt.ItemDataRole.UserRole + 1, entry['xy'])
                item.setFlags(
                    QtCore.Qt.ItemFlag.ItemIsEnabled
                    | QtCore.Qt.ItemFlag.ItemIsSelectable
                )
                self._files_list.addItem(item)
        finally:
            self._files_list.blockSignals(False)

    @staticmethod
    def _parse_porcelain_status(stdout: str) -> tuple[str, list[dict[str, str]]]:
        """
        Parse `git status --porcelain -b` output.

        Args:
            stdout (str): Raw stdout from git.

        Returns:
            tuple[str, list[dict[str, str]]]: The branch/header line (if any)
            and a list of entries with keys: 'xy' and 'path'.
        """
        header: str = ''
        entries: list[dict[str, str]] = []

        for raw_line in (stdout or '').splitlines():
            line = raw_line.rstrip('\n')
            if not line:
                continue

            if line.startswith('##'):
                header = line
                continue

            if len(line) < 3:
                continue

            xy = line[0:2]
            # Porcelain format is `XY<space><path>`.
            if line[2] != ' ':
                continue

            path = line[3:].strip()
            if not path:
                continue

            # Rename format: `R  old -> new` (keep the display as-is).
            entries.append({'xy': xy, 'path': path})

        return header, entries

    def _format_file_item_text(self, entry: dict[str, str]) -> str:
        """
        Format a single file row with a `[+]` / `[ ]` marker.

        Args:
            entry (dict[str, str]): Parsed entry.

        Returns:
            str: Display text for the list item.
        """
        xy = entry.get('xy', '  ')
        path = entry.get('path', '')
        staged = self._is_staged_from_xy(xy)
        marker = '[+]' if staged else '[ ]'
        return f'{marker} {path}'

    @staticmethod
    def _is_staged_from_xy(xy: str) -> bool:
        """
        Whether a porcelain status entry is staged.

        Args:
            xy (str): Two-character porcelain status code.
        Returns:
            bool: True if staged, otherwise False.
        """
        if len(xy) < 2:
            return False

        x = xy[0]
        # Untracked (`??`) and ignored (`!!`) are never "staged" for our UI.
        if x in {'?', '!'}:
            return False

        return x != ' '


class _GitCommandRunner(QtCore.QObject):
    """
    Manages Git command execution in a background thread.

    Args:
        parent (Optional[QtCore.QObject]): Optional Qt parent object.
    """

    result_ready = QtCore.Signal(object)

    def __init__(self, parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)
        self._thread: Optional[QtCore.QThread] = None
        self._worker: Optional[_GitWorker] = None

    @property
    def is_running(self) -> bool:
        """Whether a Git command is currently running.

        Returns:
            bool: True if a command is running.
        """
        return self._thread is not None and self._thread.isRunning()

    def run(self, repo_path: Path, args: Sequence[str]) -> None:
        """
        Start a Git command in a worker thread.

        Args:
            repo_path (Path): Path to the Git repository.
            args (Sequence[str]): Git command arguments.
        """
        if self.is_running:
            return

        self._thread = QtCore.QThread(self)
        self._worker = _GitWorker(repo_path, args)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.result_ready.connect(self._on_worker_result)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self._clear_refs)

        self._thread.start()

    def _on_worker_result(self, result: GitCommandResult) -> None:
        """Forward worker results.

        Args:
            result (GitCommandResult): Result emitted by the worker.
        """
        self.result_ready.emit(result)

    def _clear_refs(self) -> None:
        """Clear thread and worker references after completion."""
        self._thread = None
        self._worker = None


class _GitWorker(QtCore.QObject):
    """
    Worker object that executes a Git command.

    Args:
        repo_path (Path): Path to the Git repository.
        args (Sequence[str]): Git command arguments.
    """

    result_ready = QtCore.Signal(object)
    finished = QtCore.Signal()

    def __init__(self, repo_path: Path, args: Sequence[str]) -> None:
        super().__init__()
        self._repo_path = repo_path
        self._args = args

    @QtCore.Slot()
    def run(self) -> None:
        """Execute the Git command and emit the result."""
        cmd = ['git', *self._args]
        try:
            completed = subprocess.run(
                cmd,
                cwd=self._repo_path.as_posix(),
                capture_output=True,
                text=True,
                check=False,
            )
            result = GitCommandResult(
                command=' '.join(cmd),
                return_code=int(completed.returncode),
                stdout=str(completed.stdout or ''),
                stderr=str(completed.stderr or ''),
            )
        except Exception as exc:
            result = GitCommandResult(
                command=' '.join(cmd),
                return_code=1,
                stdout='',
                stderr=f'Exception running git: {exc}',
            )

        self.result_ready.emit(result)
        self.finished.emit()
