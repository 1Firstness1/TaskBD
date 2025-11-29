from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QFormLayout, QGroupBox,
    QHBoxLayout, QLineEdit, QComboBox, QCheckBox, QDialogButtonBox
)
from PySide6.QtCore import Qt

class GroupFilterDialog(QDialog):
    """Диалог группировки и фильтрации данных (устаревший для сортировки; без LIKE в WHERE)."""
    def __init__(self, controller, table_name, columns_info, selected_column, cell_value="", is_join_mode=False, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.table_name = table_name
        self.columns_info = columns_info
        self.selected_column = selected_column
        self.cell_value = cell_value
        self.is_join_mode = is_join_mode

        self.where_clause = None
        self.order_clause = None
        self.group_clause = None
        self.having_clause = None

        self.setWindowTitle(f"Группировка и фильтрация по столбцу: {selected_column}")
        self.setMinimumWidth(500)
        self.setup_ui()
        self.center_on_screen()

    def center_on_screen(self):
        screen = self.screen().geometry()
        self.move(screen.center() - self.rect().center())

    def setup_ui(self):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(f"<h3>Группировка и фильтрация по столбцу: {self.selected_column}</h3>"))

        form_layout = QFormLayout()

        filter_group = QGroupBox("Фильтрация (WHERE)")
        filter_layout = QVBoxLayout(filter_group)

        where_layout = QHBoxLayout()
        where_layout.addWidget(QLabel("Столбец:"))
        self.where_column_edit = QLineEdit(self.selected_column)
        where_layout.addWidget(self.where_column_edit)

        self.where_operator_combo = QComboBox()
        self.where_operator_combo.setMinimumWidth(150)
        self.where_operator_combo.view().setMinimumWidth(180)
        self.where_operator_combo.addItems(["=", "!=", "<", "<=", ">", ">=", "IN", "IS NULL", "IS NOT NULL"])
        where_layout.addWidget(self.where_operator_combo)

        self.where_value_edit = QLineEdit()
        if self.cell_value:
            self.where_value_edit.setText(self.cell_value)
        where_layout.addWidget(self.where_value_edit)
        filter_layout.addLayout(where_layout)

        self.where_operator_combo.currentTextChanged.connect(self.update_where_ui)
        layout.addWidget(filter_group)

        group_group = QGroupBox("Группировка (GROUP BY)")
        group_group.setStyleSheet("QGroupBox{color:#000000;}")
        group_layout = QVBoxLayout(group_group)

        self.group_check = QCheckBox(f"Группировать по столбцу: {self.selected_column}")
        self.group_check.setStyleSheet("color:#000000;")
        group_layout.addWidget(self.group_check)

        having_layout = QHBoxLayout()
        having_layout.addWidget(QLabel("HAVING:"))
        self.having_function_combo = QComboBox()
        self.having_function_combo.setMinimumWidth(140)
        self.having_function_combo.view().setMinimumWidth(180)
        self.having_function_combo.addItems(["COUNT", "SUM", "AVG", "MIN", "MAX"])
        having_layout.addWidget(self.having_function_combo)
        having_layout.addWidget(QLabel("(*)"))
        self.having_operator_combo = QComboBox()
        self.having_operator_combo.addItems(["=", "!=", "<", "<=", ">", ">="])
        self.having_operator_combo.setMinimumWidth(120)
        self.having_operator_combo.view().setMinimumWidth(150)
        having_layout.addWidget(self.having_operator_combo)
        self.having_value_edit = QLineEdit()
        having_layout.addWidget(self.having_value_edit)
        group_layout.addLayout(having_layout)
        layout.addWidget(group_group)

        layout.addStretch()
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_dialog)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.update_where_ui(self.where_operator_combo.currentText())

    def update_where_ui(self, operator_text):
        self.where_value_edit.setVisible(operator_text not in ["IS NULL", "IS NOT NULL"])

    def accept_dialog(self):
        if self.where_operator_combo.currentText() in ["IS NULL", "IS NOT NULL"]:
            self.where_clause = f"{self.where_column_edit.text()} {self.where_operator_combo.currentText()}"
        else:
            if self.where_value_edit.text().strip():
                op = self.where_operator_combo.currentText()
                if op == "IN":
                    values = [f"'{v.strip()}'" for v in self.where_value_edit.text().split(",")]
                    value = f"({', '.join(values)})"
                else:
                    try:
                        float(self.where_value_edit.text())
                        value = self.where_value_edit.text()
                    except ValueError:
                        value = f"'{self.where_value_edit.text()}'"
                self.where_clause = f"{self.where_column_edit.text()} {op} {value}"
            else:
                self.where_clause = None

        if self.group_check.isChecked():
            self.group_clause = self.selected_column
            if self.having_value_edit.text().strip():
                func = self.having_function_combo.currentText()
                op = self.having_operator_combo.currentText()
                value = self.having_value_edit.text()
                self.having_clause = f"{func}(*) {op} {value}"
            else:
                self.having_clause = None
        else:
            self.group_clause = None
            self.having_clause = None

        self.order_clause = None
        self.accept()