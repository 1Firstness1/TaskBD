from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QGroupBox, QCheckBox, QComboBox,
    QLineEdit, QDialogButtonBox, QMessageBox
)

class GroupDialog(QDialog):
    """Диалог группировки с выбором агрегатной функции и HAVING."""
    def __init__(self, column, columns_info, parent=None):
        super().__init__(parent)
        self.column = column
        self.columns_info = columns_info
        self.group_by_selected = True
        self.group_by_column = column
        self.aggregate_expression = None
        self.having_clause = None

        self.setWindowTitle(f"Группировка: {self.column}")
        self.setMinimumWidth(640)
        self.setup_ui()
        self.center_on_screen()

    def center_on_screen(self):
        screen = self.screen().geometry()
        self.move(screen.center() - self.rect().center())

    def setup_ui(self):
        layout = QVBoxLayout(self)
        checkbox_style = """
        QCheckBox { color: #333333; }
        QCheckBox::indicator {
            width: 14px; height: 14px;
            border: 1px solid #c0c0c0; border-radius: 3px; background: white;
        }
        QCheckBox::indicator:checked {
            background-color: #4a86e8; border: 1px solid #2a66c8;
        }
        """

        gb_group = QGroupBox("Группировка (GROUP BY)")
        gb_group.setStyleSheet("color: #333333;")
        gb_layout = QFormLayout(gb_group)

        self.gb_check = QCheckBox("Включить GROUP BY")
        self.gb_check.setChecked(True)
        self.gb_check.setStyleSheet(checkbox_style)
        gb_layout.addRow(self.gb_check)

        self.gb_col_combo = QComboBox()
        self.gb_col_combo.setMinimumWidth(200)
        self.gb_col_combo.view().setMinimumWidth(240)
        self.gb_col_combo.addItems([c['name'] for c in self.columns_info])
        self.gb_col_combo.setCurrentText(self.column)
        gb_layout.addRow("Столбец для группировки:", self.gb_col_combo)
        layout.addWidget(gb_group)

        agg_group = QGroupBox("Агрегатная функция")
        agg_group.setStyleSheet("color: #333333;")
        agg_form = QFormLayout(agg_group)

        self.agg_func = QComboBox()
        self.agg_func.setMinimumWidth(200)
        self.agg_func.view().setMinimumWidth(240)
        self.agg_func.addItems(["(нет)", "COUNT(*)", "COUNT", "SUM", "AVG", "MIN", "MAX"])
        agg_form.addRow("Функция:", self.agg_func)

        self.agg_target_combo = QComboBox()
        self.agg_target_combo.setMinimumWidth(200)
        self.agg_target_combo.view().setMinimumWidth(240)
        self.agg_target_combo.addItems([c['name'] for c in self.columns_info])
        self.agg_target_combo.setCurrentText(self.column)
        agg_form.addRow("Столбец для агрегата:", self.agg_target_combo)

        self.alias_edit = QLineEdit()
        agg_form.addRow("Псевдоним:", self.alias_edit)
        layout.addWidget(agg_group)

        having_group = QGroupBox("Фильтрация групп (HAVING)")
        having_group.setStyleSheet("color: #333333;")
        having_form = QFormLayout(having_group)

        self.having_enable = QCheckBox("Включить HAVING")
        self.having_enable.setChecked(False)
        self.having_enable.setStyleSheet(checkbox_style)
        having_form.addRow(self.having_enable)

        self.having_op = QComboBox()
        self.having_op.setMinimumWidth(140)
        self.having_op.view().setMinimumWidth(170)
        self.having_op.addItems(["=", "!=", "<", "<=", ">", ">="])
        having_form.addRow("Оператор:", self.having_op)

        self.having_value = QLineEdit()
        having_form.addRow("Значение:", self.having_value)
        layout.addWidget(having_group)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_dialog)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._toggle_agg_target()
        self.agg_func.currentTextChanged.connect(self._toggle_agg_target)
        self._toggle_having_ui()
        self.having_enable.stateChanged.connect(self._toggle_having_ui)

    def _toggle_agg_target(self):
        func = self.agg_func.currentText()
        self.agg_target_combo.setEnabled(func not in ("(нет)", "COUNT(*)"))

    def _toggle_having_ui(self):
        enabled = self.having_enable.isChecked()
        self.having_op.setEnabled(enabled)
        self.having_value.setEnabled(enabled)

    @staticmethod
    def _is_number(s):
        try:
            float(s)
            return True
        except ValueError:
            return False

    def _build_agg_expr(self):
        func_choice = self.agg_func.currentText()
        target_col = self.agg_target_combo.currentText()
        if func_choice == "(нет)":
            return None, None
        if func_choice == "COUNT(*)":
            base = "COUNT(*)"
        elif func_choice == "COUNT":
            base = f"COUNT({target_col})"
        else:
            base = f"{func_choice}({target_col})"
        alias = self.alias_edit.text().strip()
        expr = f"{base} AS {alias}" if alias else base
        return base, expr

    def accept_dialog(self):
        self.group_by_selected = self.gb_check.isChecked()
        self.group_by_column = self.gb_col_combo.currentText()
        base_func, expr = self._build_agg_expr()
        self.aggregate_expression = expr

        if self.having_enable.isChecked():
            if not base_func:
                QMessageBox.warning(self, "Ошибка", "Для HAVING выберите агрегатную функцию")
                return
            op = self.having_op.currentText()
            val_str = self.having_value.text().strip()
            if not val_str:
                QMessageBox.warning(self, "Ошибка", "Введите значение для HAVING")
                return
            value = val_str if self._is_number(val_str) else f"'{val_str}'"
            self.having_clause = f"{base_func} {op} {value}"
        else:
            self.having_clause = None

        self.accept()