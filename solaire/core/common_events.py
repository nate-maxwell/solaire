"""
# Common Events

* Description:

    Events commonly shared between various widgets, such as the toolbar,
    shortcuts, or individual component widgets.
"""


from pathlib import Path

from PySide6 import QtWidgets

from solaire.core import broker
from solaire.core import evaluator


broker.register_source('common_event')


def save_file() -> None:
    """Save the currently active file. Emits None."""
    event = broker.Event('common_event', 'save_file')
    broker.emit(event)


def save_all() -> None:
    """Save all files. Emits None."""
    event = broker.Event('common_event', 'save_all')
    broker.emit(event)


def open_file() -> None:
    """Open a file dialog and open the selected file.
    Emits selected filepath.
    """
    file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
        None,
        'Select a File',
        '',
        'All Files (*);;Python Files (*.py);;Text Files (*.txt)'
    )

    if not file_path:
        return

    event = broker.Event('common_event', 'open_file', Path(file_path))
    broker.emit(event)


def open_folder() -> None:
    """Open a file dialog and switch the active project to the selected folder.
    Emits selected filepath.
    """
    dir_path = QtWidgets.QFileDialog.getExistingDirectory(
        None,
        'Select a File',
        '',
        QtWidgets.QFileDialog.Option.ShowDirsOnly
    )

    if not dir_path:
        return

    new_path = Path(dir_path)
    event = broker.Event('common_event', 'open_folder', new_path)
    broker.emit(event)
    evaluator.update_project_path(new_path)


def toggle_explorer() -> None:
    """Signal to toggle visibility on file explorer. Emits None."""
    event = broker.Event('side_bar', 'toggle_explorer')
    broker.emit(event)


def toggle_structure() -> None:
    """Signal to toggle visibility on structure explorer. Emits None."""
    event = broker.Event('side_bar', 'toggle_structure')
    broker.emit(event)


def toggle_git_menu() -> None:
    """Signal to toggle visibility on git commit menu. Emits None."""
    event = broker.Event('side_bar', 'toggle_git')
    broker.emit(event)


def toggle_full_screen() -> None:
    """Signal to toggle full screen. Emits None."""
    event = broker.Event('window', 'toggle_full_screen')
    broker.emit(event)


def show_output() -> None:
    """Show the output tab widget if it is hidden."""
    event = broker.Event('SYSTEM', 'SHOW_OUTPUT')
    broker.emit(event)


def run_code() -> None:
    """Run the active file's code. Emits None."""
    event = broker.Event('SYSTEM', 'RUN')
    broker.emit(event)


def flush_output() -> None:
    """Clears stdout and stderr. Emits None."""
    event = broker.Event('SYSTEM', 'FLUSH')
    broker.emit(event)
