"""
Standalone application entry point.

Solaire can alwasy be inherited from to create DCC specific versions, parented
to the DCC main window via DCC API.
"""

import sys

from PySide6TK import QtWrappers

from solaire.core.client import SolaireClientWindow


def main() -> int:
    return QtWrappers.exec_app(
        SolaireClientWindow,
        'SolaireClientWindow'
    )


if __name__ == '__main__':
    sys.exit(main())
