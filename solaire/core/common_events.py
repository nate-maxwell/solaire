from pathlib import Path

from PySide6 import QtWidgets

from solaire.core import broker


def save_file() -> None:
    """Save the currently active file. Emits None."""
    event = broker.Event('shortcut_manager', 'save_file')
    broker.emit(event)


def save_all() -> None:
    """Save all files. Emits None."""
    event = broker.Event('shortcut_manager', 'save_all')
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

    event = broker.Event('shortcut_manager', 'open_file', Path(file_path))
    broker.emit(event)


def toggle_explorer() -> None:
    """Signal to toggle visibility on file explorer."""
    event = broker.Event('sections_bar', 'toggle_explorer')
    broker.emit(event)


def toggle_structure() -> None:
    """Signal to toggle visibility on structure explorer."""
    event = broker.Event('sections_bar', 'toggle_structure')
    broker.emit(event)


def run_code() -> None:
    """Run the active file's code. Emits None."""
    event = broker.Event('SYSTEM', 'RUN', None)
    broker.emit(event)
