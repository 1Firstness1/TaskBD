from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QComboBox, QCheckBox, QDialogButtonBox, QMessageBox
)

class AddColumnDialog(QDialog):
    """Диалог добавления нового столбца."""
    def __init__(self, controller, table_name, user_types=None, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.table_name = table_name
        self.user_types = user_types or []

        self.setWindowTitle("Добавить столбец")
        self.setMinimumWidth(400)
        self.setup_ui()
        self.center_on_screen()

    def center_on_screen(self):
        screen = self.screen().geometry()
        self.move(screen.center() - self.rect().center())

    def setup_ui(self):
        layout = QFormLayout(self)

        checkbox_style = """
            QCheckBox {
                color: #333333;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border: 1px solid #c0c0c0;
                border-radius: 3px;
                background: white;
            }
            QCheckBox::indicator:hover {
                border: 1px solid #3a76d8;
                background: #f0f6ff;
            }
            QCheckBox::indicator:checked {
                background-color: #4a86e8;
                border: 1px solid #2a66c8;
                image: none;
            }
            QCheckBox::indicator:checked:hover {
                background-color: #3a76d8;
            }
        """

        self.name_edit = QLineEdit()
        layout.addRow("Имя столбца:", self.name_edit)

        self.type_combo = QComboBox()
        self.type_combo.setMinimumWidth(220)
        self.type_combo.view().setMinimumWidth(260)

        base_types = [
            "INTEGER", "BIGINT", "VARCHAR(100)", "VARCHAR(200)",
            "TEXT", "BOOLEAN", "DATE", "TIMESTAMP", "NUMERIC"
        ]
        for t in base_types:
            self.type_combo.addItem(t)

        if self.user_types:
            self.type_combo.insertSeparator(self.type_combo.count())
            for ut in self.user_types:
                self.type_combo.addItem(f"{ut} (user type)", ut)

        layout.addRow("Тип данных:", self.type_combo)

        self.nullable_check = QCheckBox("Может быть NULL")
        self.nullable_check.setChecked(True)
        self.nullable_check.setStyleSheet(checkbox_style)
        layout.addRow("", self.nullable_check)

        self.default_edit = QLineEdit()
        layout.addRow("Значение по умолчанию:", self.default_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_dialog)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _current_type_value(self):
        idx = self.type_combo.currentIndex()
        data = self.type_combo.itemData(idx)
        if data:
            return data
        text = self.type_combo.currentText()
        if " (user type)" in text:
            return text.split(" (user type)", 1)[0]
        return text

    def accept_dialog(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите имя столбца")
            return

        data_type = self._current_type_value()
        nullable = self.nullable_check.isChecked()
        default = self.default_edit.text().strip() if self.default_edit.text().strip() else None

        success, error = self.controller.add_column(
            self.table_name, name, data_type, nullable, default
        )

        if success:
            QMessageBox.information(self, "Успех", f"Столбец '{name}' успешно добавлен")
            self.accept()
        else:
            QMessageBox.critical(self, "Ошибка", f"Не удалось добавить столбец:\n{error}")