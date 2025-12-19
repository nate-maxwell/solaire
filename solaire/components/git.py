"""
Qt-based Git UI widget for basic repository operations.

This module provides a QWidget that exposes common Git commands
(commit, push, pull, status) and executes them asynchronously
using a worker thread to avoid blocking the UI.
"""

# TODO: Replace the output QPlainTextEdit with a menu that builds buttons for
#  each file that needs to be marked for an operation.


import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from typing import Sequence

from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets

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

        self._runner: _GitCommandRunner = _GitCommandRunner(self)
        self._create_widgets()
        self._create_layout()
        self._create_connections()
        self._create_subscriptions()

        self._set_busy(False)
        self._append_output(f'Repo: {self._repo_path.as_posix()}')
        self._refresh_status()

    def _create_widgets(self) -> None:
        """Create child widgets used by the Git widget."""
        self._message_line_edit = QtWidgets.QLineEdit(self)
        self._message_line_edit.setPlaceholderText('Commit message (required)')

        self._commit_button = QtWidgets.QPushButton(self)
        self._commit_button.setText('Commit')
        self._push_button = QtWidgets.QPushButton(self)
        self._push_button.setText('Push')
        self._pull_button = QtWidgets.QPushButton(self)
        self._pull_button.setText('Pull')
        self._status_button = QtWidgets.QPushButton(self)
        self._status_button.setText('Status')

        self._progress = QtWidgets.QProgressBar(self)
        self._progress.setRange(0, 0)
        self._progress.setVisible(False)

        self._output = QtWidgets.QPlainTextEdit(self)
        self._output.setLineWrapMode(QtWidgets.QPlainTextEdit.LineWrapMode.NoWrap)
        self._output.setReadOnly(True)

    def _create_layout(self) -> None:
        """Assemble the widget layout."""
        buttons_row = QtWidgets.QHBoxLayout()
        buttons_row.addWidget(self._commit_button)
        buttons_row.addWidget(self._push_button)
        buttons_row.addWidget(self._pull_button)
        buttons_row.addWidget(self._status_button)
        buttons_row.addStretch(1)

        root = QtWidgets.QVBoxLayout(self)
        root.addWidget(self._message_line_edit)
        root.addLayout(buttons_row)
        root.addWidget(self._progress)
        root.addWidget(self._output, 1)

        self.setLayout(root)

    def _create_connections(self) -> None:
        """Connect signals to their respective slots."""
        self._commit_button.clicked.connect(self._on_commit_clicked)
        self._push_button.clicked.connect(self._on_push_clicked)
        self._pull_button.clicked.connect(self._on_pull_clicked)
        self._status_button.clicked.connect(self._on_status_clicked)

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
        self._output.clear()
        self.set_repo_path(event.data)

    def set_repo_path(self, repo_path: Path) -> None:
        """
        Update the active Git repository path.

        Args:
            repo_path (Path): New repository path.
        """
        self._repo_path = repo_path
        self._append_output(f'Repo: {self._repo_path.as_posix()}')
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

    def _on_status_clicked(self) -> None:
        """Handle Status button click."""
        self._refresh_status()

    def _refresh_status(self) -> None:
        """Run a Git status command."""
        self._run_git(['status', '--porcelain', '-b'])

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
            self._append_output('A git command is already running.')
            return

        self._set_busy(True)
        self._append_output(f'$ git {" ".join(args)}')
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
        self._status_button.setEnabled(not busy)
        self._message_line_edit.setEnabled(not busy)

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
        Append command output to the output console.

        For `git status --porcelain` output, each line starts with a
        two-character status code (`XY`). This formats any valid porcelain
        status code prefix into a bracketed form like `[ XY ]`.

        Valid porcelain codes include (as individual characters within `XY`):
        ' ' (space), M, A, D, R, C, U, ?, !.

        Args:
            result (GitCommandResult): Result of the completed Git command.
        """

        def _format_porcelain_status_prefix(line_: str) -> str:
            if len(line_) < 3:
                return line_

            x = line_[0]
            y = line_[1]
            sep = line_[2]

            # Porcelain format is `XY<space>...` (or `XY<space><path>`).
            if sep != ' ':
                return line_

            valid = {' ', 'M', 'A', 'D', 'R', 'C', 'U', '?', '!'}
            if x not in valid or y not in valid:
                return line_

            remainder = line_[2:]  # includes the leading space before the path
            return f'[ {x}{y} ]{remainder}'

        if result.stdout.strip():
            for line in result.stdout.rstrip().splitlines():
                self._append_output(_format_porcelain_status_prefix(line))

        if result.stderr.strip():
            self._append_output(result.stderr.rstrip())

        if result.return_code != 0:
            self._append_output(f'[exit {result.return_code}]')
        else:
            self._append_output('[-OK-]')

    def _append_output(self, text: str) -> None:
        """
        Append text to the output console and scroll to bottom.

        Args:
            text (str): Text to append.
        """
        self._output.appendPlainText(text)
        cursor = self._output.textCursor()
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
        self._output.setTextCursor(cursor)
        self._output.ensureCursorVisible()


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
        """Start a Git command in a worker thread.

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
