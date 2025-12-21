from pathlib import Path
from typing import Optional
from typing import Union

import git
from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets

from solaire.core import appdata
from solaire.core import timers


MODIFIED = 'MOD'
UNTRACKED = 'UNT'
ADDED = 'ADD'
DELETED = 'DEL'

COLORS = {
    MODIFIED: 'orange',
    UNTRACKED: 'cyan',
    ADDED: 'green',
    DELETED: 'red'
}


def get_repo_status() -> dict[Path, str]:
    """
    Returns a dict of { Path() : status_str } outlining all the files presently
    in the repo.

    Returns:
        dict[Path, str].
    """
    repo = git.Repo(appdata.SessionData().project_directory)
    if repo.bare:
        return {}

    status = {}

    # Modified and Deleted
    for item in repo.index.diff(None):
        if item.deleted_file:
            status[Path(item.a_path)] = DELETED
        else:
            status[Path(item.a_path)] = MODIFIED

    # Untracked
    for file in repo.untracked_files:
        status[Path(file)] = UNTRACKED

    # Staged
    for item in repo.index.diff('HEAD'):
        if Path(item.a_path) not in status:
            status[Path(item.a_path)] = ADDED

    return status


TreeItemParent = Union[QtWidgets.QTreeWidget, QtWidgets.QTreeWidgetItem]


class CommitTreeItem(QtWidgets.QTreeWidgetItem):
    def __init__(
        self,
        path: Path,
        parent: Optional[TreeItemParent] = None,
        color: str = 'white',
        strings: Optional[list[str]] = None
    ) -> None:
        super().__init__(parent, strings)
        self.path = path
        self.setForeground(0, QtGui.QBrush(QtGui.QColor(color)))
        self.setCheckState(0, QtCore.Qt.CheckState.Unchecked)


class GitCommitWidget(QtWidgets.QWidget):
    def __init__(
            self,
            visible: bool = False,
            parent: Optional[QtWidgets.QWidget] = None
    ) -> None:
        super().__init__(parent)
        self.setVisible(visible)

        self._create_widgets()
        self._create_layout()
        self._create_connections()
        self._create_timers()
        self.refresh()

    def _create_widgets(self) -> None:
        self.layout_main = QtWidgets.QVBoxLayout()
        self.layout_main.setContentsMargins(0, 0, 0, 0)

        # -----File Status-----
        self.tree_widget = QtWidgets.QTreeWidget()
        self.tree_widget.setHeaderLabel('Commit')
        font = QtGui.QFont('Courier New', 10)
        self.tree_widget.setFont(font)
        self.tree_widget.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.NoSelection
        )

        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)

        # -----Commit Handling-----
        self.wid_commit = QtWidgets.QWidget()

        self.hlayout_mark = QtWidgets.QHBoxLayout()
        self.btn_mark_all = QtWidgets.QPushButton('Check All')
        self.btn_unmark_all = QtWidgets.QPushButton('Uncheck All')

        self.vlayout_commit = QtWidgets.QVBoxLayout()
        self.vlayout_commit.setContentsMargins(0, 0, 0, 0)

        self.pte_commit_message = QtWidgets.QPlainTextEdit()
        self.pte_commit_message.setPlaceholderText('Commit Message')

        self.hlayout_buttons = QtWidgets.QHBoxLayout()
        self.btn_refresh = QtWidgets.QPushButton('Refresh')
        self.btn_commit = QtWidgets.QPushButton('Commit')
        self.btn_commit_push = QtWidgets.QPushButton('Commit and Push...')

    def _create_layout(self) -> None:
        self.hlayout_mark.addWidget(self.btn_mark_all)
        self.hlayout_mark.addWidget(self.btn_unmark_all)

        self.hlayout_buttons.addWidget(self.btn_refresh)
        self.hlayout_buttons.addWidget(self.btn_commit)
        self.hlayout_buttons.addWidget(self.btn_commit_push)

        self.vlayout_commit.addLayout(self.hlayout_mark)
        self.vlayout_commit.addWidget(self.pte_commit_message)
        self.vlayout_commit.addLayout(self.hlayout_buttons)
        self.wid_commit.setLayout(self.vlayout_commit)

        self.splitter.addWidget(self.tree_widget)
        self.splitter.addWidget(self.wid_commit)

        self.layout_main.addWidget(self.splitter)
        self.setLayout(self.layout_main)

    def _create_connections(self) -> None:
        self.btn_mark_all.clicked.connect(self.check_all)
        self.btn_unmark_all.clicked.connect(self.uncheck_all)
        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_commit.clicked.connect(self.commit)
        self.btn_commit_push.clicked.connect(self.commit_and_push)

    def _create_timers(self) -> None:
        self.refresh_timer = timers.create_bind_and_start_timer(
            self,
            1500,
            self.refresh,
            single_shot=False
        )
        self.refresh_timer.start()

    def refresh(self) -> None:
        for k, v in get_repo_status().items():
            spacing = 20-len(k.name)
            spacer = ' ' * (spacing + 2)
            label = f'[{v}] {k.name}{spacer}{k.parent}'
            if self._check_item_exists(label):
                continue

            color = COLORS[v]
            item = CommitTreeItem(k, self.tree_widget, color, [label])
            self.tree_widget.addTopLevelItem(item)

    def _check_item_exists(self, text: str) -> bool:
        items = self.tree_widget.findItems(
            text, QtCore.Qt.MatchFlag.MatchExactly, 0
        )
        return len(items) > 0

    def check_all(self) -> None:
        """Check all items in the tree widget."""
        for i in range(self.tree_widget.topLevelItemCount()):
            item = self.tree_widget.topLevelItem(i)
            if item:
                item.setCheckState(0, QtCore.Qt.CheckState.Checked)

    def uncheck_all(self) -> None:
        """Uncheck all items in the tree widget."""
        for i in range(self.tree_widget.topLevelItemCount()):
            item = self.tree_widget.topLevelItem(i)
            if item:
                item.setCheckState(0, QtCore.Qt.CheckState.Unchecked)

    def commit(self) -> bool:
        """Commit all checked files with the provided commit message."""
        commit_message = self.pte_commit_message.toPlainText().strip()

        if not commit_message:
            QtWidgets.QMessageBox.warning(
                self,
                'No Commit Message',
                'Please provide a commit message.'
            )
            return False

        checked_files = self._get_checked_files()

        if not checked_files:
            QtWidgets.QMessageBox.warning(
                self,
                'No Files Selected',
                'Please check at least one file to commit.'
            )
            return False

        try:
            repo = git.Repo(appdata.SessionData().project_directory)
            repo.index.add([str(f) for f in checked_files])
            repo.index.commit(commit_message)

            self.pte_commit_message.clear()
            self.tree_widget.clear()
            self.refresh()

            QtWidgets.QMessageBox.information(
                self,
                'Commit Successful',
                f'Successfully committed {len(checked_files)} file(s).'
            )

            return True

        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                'Commit Failed',
                f'Failed to commit: {str(e)}'
            )
            self.pte_commit_message.setPlainText(commit_message)
            return False

    def commit_and_push(self) -> None:
        """Commit all checked files and push to remote."""
        if not self.commit():
            return

        try:
            repo = git.Repo(appdata.SessionData().project_directory)
            origin = repo.remote(name='origin')
            origin.push()

            QtWidgets.QMessageBox.information(
                self,
                'Push Successful',
                'Successfully pushed to remote.'
            )

        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                'Push Failed',
                f'Failed to push: {str(e)}'
            )

    def _get_checked_files(self) -> list[Path]:
        """Get all files that are checked in the tree widget."""
        checked_files = []

        for i in range(self.tree_widget.topLevelItemCount()):
            item = self.tree_widget.topLevelItem(i)
            if isinstance(item, CommitTreeItem) and item.checkState(
                    0) == QtCore.Qt.CheckState.Checked:
                checked_files.append(item.path)

        return checked_files

    def mark_all(self) -> None:
        ...

    def unmark_all(self) -> None:
        ...
