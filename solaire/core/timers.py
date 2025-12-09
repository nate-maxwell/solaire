"""
Boilerplate and utilities for starting and managing QTimers.

Honestly, this mostly exists because I keep forgetting all of the necessary
settings on QTimers.
"""

from typing import Any
from typing import Callable
from typing import Union

from PySide6 import QtCore
from PySide6 import QtWidgets


Connectable = Union[QtCore.SignalInstance, Callable[..., Any]]


def create_bind_and_start_timer(
        parent: QtWidgets.QWidget,
        interval: int,
        trigger: QtCore.SignalInstance,
        connected_on_timeout: Connectable,
        single_shot: bool = True
) -> QtCore.QTimer:
    """Create a QTimer, bind its timeout, hook a starter signal, and return it.

        Args:
            parent (QtWidgets.QWidget): QWidget that will own the timer.
            interval (int): Interval in milliseconds.
            trigger (SignalInstance): A Qt signal that, when emitted, starts
                the timer. This should be a zero-argument signal to match
                QTimer.start().
            connected_on_timeout (Connectable): Target to connect to
                QTimer.timeout (another signal or a zero-arg callable).
            single_shot (bool): If True, timer fires once; otherwise it
                repeats. Defaults to True

        Returns:
            The configured QTimer instance.
        """
    timer = QtCore.QTimer(parent)
    timer.setInterval(interval)
    timer.setSingleShot(single_shot)
    timer.timeout.connect(connected_on_timeout)
    trigger.connect(timer.start)

    return timer
