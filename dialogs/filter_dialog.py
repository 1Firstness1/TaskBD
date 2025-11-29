from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QLineEdit, QDialogButtonBox, QMessageBox
)

class FilterDialog(QDialog):
    """Диалог фильтрации WHERE для одного столбца."""
    def __init__(self, column, prefill_value="", parent=None):
        super().__init__(parent)
        self.column = column
        self.prefill_value = prefill_value
        self.where_clause = None

        self.setWindowTitle(f"Фильтрация (WHERE): {self.column}")
        self.setMinimumWidth(520)
        self.setup_ui()
        self.center_on_screen()

    def center_on_screen(self):
        screen = self.screen().geometry()
        self.move(screen.center() - self.rect().center())

    def setup_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.op_combo = QComboBox()
        self.op_combo.setMinimumWidth(150)
        self.op_combo.view().setMinimumWidth(180)
        self.op_combo.addItems(["=", "!=", "<", "<=", ">", ">=", "IN", "IS NULL", "IS NOT NULL"])
        form.addRow("Оператор:", self.op_combo)

        self.value_edit = QLineEdit()
        if self.prefill_value:
            self.value_edit.setText(self.prefill_value)
        form.addRow("Значение:", self.value_edit)
        layout.addLayout(form)

        self.op_combo.currentTextChanged.connect(self._toggle_value)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_dialog)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._toggle_value(self.op_combo.currentText())

    def _toggle_value(self, op):
        self.value_edit.setVisible(op not in ("IS NULL", "IS NOT NULL"))

    def accept_dialog(self):
        op = self.op_combo.currentText()
        if op in ("IS NULL", "IS NOT NULL"):
            self.where_clause = f"{self.column} {op}"
        else:
            val = self.value_edit.text().strip()
            if not val:
                QMessageBox.warning(self, "Ошибка", "Введите значение фильтра")
                return
            if op == "IN":
                parts = [p.strip() for p in val.split(",") if p.strip()]
                quoted = ", ".join([f"'{p}'" if not self._is_number(p) else p for p in parts])
                self.where_clause = f"{self.column} IN ({quoted})"
            else:
                value = val if self._is_number(val) else f"'{val}'"
                self.where_clause = f"{self.column} {op} {value}"
        self.accept()

    @staticmethod
    def _is_number(s):
        try:
            float(s)
            return True
        except ValueError:
            return False