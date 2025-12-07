from typing import Optional

import jedi
from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets

from solaire.core import broker


class CodeStructureWidget(QtWidgets.QTreeWidget):
    line_clicked = QtCore.Signal(int)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setHeaderLabel('Structure')
        self.setColumnCount(1)
        self.itemClicked.connect(self.on_item_clicked)
        self._create_subscriptions()

    def _create_subscriptions(self) -> None:
        broker.register_source('structure_explorer')

        broker.register_subscriber(
            'tab_manager',
            'active_changed',
            self._tab_changed_subscription
        )
        broker.register_subscriber(
            'tab_manager',
            'all_tabs_closed',
            self._all_tabs_closed_subscription
        )

    def _tab_changed_subscription(self, event: broker.Event) -> None:
        self.update_structure(event.data.toPlainText())

    def _all_tabs_closed_subscription(self, _: broker.Event) -> None:
        self.update_structure('')

    def update_structure(self, code: str) -> None:
        """Parse code and update the tree structure."""
        self.clear()

        if not code.strip():
            return

        try:
            script = jedi.Script(code)
            names = script.get_names(all_scopes=True, definitions=True)

            classes = {}
            functions = []

            for name in names:
                if name.type == 'class':
                    classes[name.name] = {
                        'item': name,
                        'methods': []
                    }
                elif name.type == 'function':
                    # Check if it belongs to a class
                    parent_context = name.parent()
                    if parent_context and parent_context.type == 'class':
                        parent_name = parent_context.name
                        if parent_name in classes:
                            classes[parent_name]['methods'].append(name)
                    else:
                        functions.append(name)

            for class_name, class_data in sorted(classes.items()):
                class_item = QtWidgets.QTreeWidgetItem(self)
                class_item.setText(0, f'📦 {class_name}')
                class_item.setData(
                    0,
                    QtCore.Qt.ItemDataRole.UserRole,
                    class_data['item'].line
                )

                font = QtGui.QFont()
                font.setBold(True)
                class_item.setFont(0, font)

                for method in sorted(class_data['methods'],
                                     key=lambda x: x.line):
                    method_item = QtWidgets.QTreeWidgetItem(class_item)
                    method_item.setText(0, f'  🔧 {method.name}()')
                    method_item.setData(
                        0,
                        QtCore.Qt.ItemDataRole.UserRole,
                        method.line
                    )

                class_item.setExpanded(True)

            for func in sorted(functions, key=lambda x: x.line):
                func_item = QtWidgets.QTreeWidgetItem(self)
                func_item.setText(0, f'⚙️ {func.name}()')
                func_item.setData(
                    0,
                    QtCore.Qt.ItemDataRole.UserRole,
                    func.line
                )

        except Exception as e:
            error_item = QtWidgets.QTreeWidgetItem(self)
            error_item.setText(0, f'Error parsing: {str(e)}')

    @staticmethod
    def on_item_clicked(item: QtWidgets.QTreeWidgetItem) -> None:
        """Emit signal when item is clicked with line number."""
        line = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        if not line:
            return

        event = broker.Event('structure_explorer', 'item_clicked', line)
        broker.emit(event)
