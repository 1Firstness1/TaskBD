from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QCheckBox, QGroupBox, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QFormLayout, QDialogButtonBox, QHBoxLayout, QMessageBox
)
from PySide6.QtCore import Qt

class CaseExpressionDialog(QDialog):
    """Конструктор CASE + COALESCE + NULLIF (без неправильного COALESCE)."""
    def __init__(self, controller, table_name, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.table_name = table_name
        self.setWindowTitle("Конструктор CASE / COALESCE / NULLIF")
        self.setMinimumWidth(700)
        self.when_rows = []
        self.case_alias_edit = None
        self.else_edit = None
        self.coalesce_value_edit = None
        self.coalesce_col_combo = None
        self.nullif_first_edit = None
        self.nullif_second_edit = None
        self.case_group = None
        self.case_enable_check = None
        self.final_expr = None
        self.setup_ui()

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

        self.case_enable_check = QCheckBox("Использовать CASE (WHEN ... THEN ...)")
        self.case_enable_check.setChecked(True)
        self.case_enable_check.setStyleSheet(checkbox_style)
        layout.addWidget(self.case_enable_check)

        self.case_group = QGroupBox("CASE выражение")
        case_layout = QVBoxLayout(self.case_group)
        case_layout.addWidget(QLabel("Условия WHEN ... THEN ..."))
        self.when_container = QVBoxLayout()
        case_layout.addLayout(self.when_container)

        add_when_btn = QPushButton("Добавить WHEN")
        add_when_btn.clicked.connect(self.add_when_row)
        case_layout.addWidget(add_when_btn)

        case_layout.addWidget(QLabel("Значение ELSE (опционально):"))
        self.else_edit = QLineEdit()
        case_layout.addWidget(self.else_edit)

        layout.addWidget(self.case_group)

        layout.addWidget(QLabel("Алиас (имя нового столбца):"))
        self.case_alias_edit = QLineEdit()
        layout.addWidget(self.case_alias_edit)

        coalesce_group = QGroupBox("COALESCE (замена NULL)")
        coalesce_layout = QFormLayout(coalesce_group)

        cols_info = self.controller.get_table_columns(self.table_name)
        self.coalesce_col_combo = QComboBox()
        self.coalesce_col_combo.setMinimumWidth(180)
        self.coalesce_col_combo.view().setMinimumWidth(210)
        self.coalesce_col_combo.addItems([c['name'] for c in cols_info])
        coalesce_layout.addRow("Столбец для COALESCE:", self.coalesce_col_combo)

        self.coalesce_value_edit = QLineEdit()
        self.coalesce_value_edit.setPlaceholderText("Значение по умолчанию для NULL (например: Категория не указана)")
        coalesce_layout.addRow("Значение:", self.coalesce_value_edit)
        layout.addWidget(coalesce_group)

        layout.addWidget(QLabel("NULLIF (если expr1 == expr2 → NULL, опционально):"))
        nullif_layout = QHBoxLayout()
        self.nullif_first_edit = QLineEdit()
        self.nullif_first_edit.setPlaceholderText("expr1 (например, имя столбца: category)")
        self.nullif_second_edit = QLineEdit()
        self.nullif_second_edit.setPlaceholderText("expr2 (например, Продажи)")
        nullif_layout.addWidget(self.nullif_first_edit)
        nullif_layout.addWidget(self.nullif_second_edit)
        layout.addLayout(nullif_layout)

        btn_layout = QHBoxLayout()
        build_btn = QPushButton("Добавить выражение")
        cancel_btn = QPushButton("Отмена")
        btn_layout.addWidget(build_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        build_btn.clicked.connect(self.build_expression)
        cancel_btn.clicked.connect(self.reject)

        self.case_enable_check.stateChanged.connect(self._toggle_case_block)
        self.add_when_row()

    def _toggle_case_block(self, state):
        self.case_group.setEnabled(state == Qt.Checked)

    def add_when_row(self):
        row_layout = QHBoxLayout()
        cols_info = self.controller.get_table_columns(self.table_name)

        col_combo = QComboBox()
        col_combo.setMinimumWidth(150)
        col_combo.view().setMinimumWidth(180)
        col_combo.addItems([c['name'] for c in cols_info])

        op_combo = QComboBox()
        op_combo.setMinimumWidth(120)
        op_combo.view().setMinimumWidth(150)
        op_combo.addItems(["=", "!=", ">", "<", ">=", "<=", "IS NULL", "IS NOT NULL"])

        when_value_edit = QLineEdit()
        when_value_edit.setPlaceholderText("Значение для сравнения (кроме IS NULL)")
        then_value_edit = QLineEdit()
        then_value_edit.setPlaceholderText("THEN (результат)")

        row_layout.addWidget(col_combo)
        row_layout.addWidget(op_combo)
        row_layout.addWidget(when_value_edit)
        row_layout.addWidget(QLabel("THEN"))
        row_layout.addWidget(then_value_edit)

        self.when_container.addLayout(row_layout)
        self.when_rows.append((col_combo, op_combo, when_value_edit, then_value_edit))

    def _quote_if_needed(self, val: str):
        """Правильная обработка значений для SQL: числа не кавычим, строки кавычим."""
        if val is None:
            return "NULL"
        val = val.strip()
        if val == "":
            return "''"
        # Если значение уже в кавычках, возвращаем как есть
        if (val.startswith("'") and val.endswith("'")) or (val.startswith('"') and val.endswith('"')):
            return val
        # Если это число (int или float), не кавычим
        try:
            float(val)
            return val
        except ValueError:
            pass
        # Если это имя столбца или выражение (содержит точку или скобки), не кавычим
        if '.' in val or '(' in val or ' ' in val:
            return val
        # Иначе это строка - кавычим и экранируем одинарные кавычки
        escaped = val.replace("'", "''")
        return f"'{escaped}'"

    def build_expression(self):
        use_case = self.case_enable_check.isChecked()
        expr = None
        has_when = False

        if use_case:
            parts = ["CASE"]
            for col_combo, op_combo, when_edit, then_edit in self.when_rows:
                col = col_combo.currentText()
                if not col:
                    continue  # Пропускаем пустые строки
                op = op_combo.currentText()
                when_raw = when_edit.text().strip()
                then_raw = then_edit.text().strip()

                if op in ("IS NULL", "IS NOT NULL"):
                    if not then_raw:
                        continue
                    parts.append(
                        f"WHEN {self.table_name}.{col} {op} "
                        f"THEN {self._quote_if_needed(then_raw)}"
                    )
                    has_when = True
                else:
                    if not when_raw or not then_raw:
                        continue
                    q_when = self._quote_if_needed(when_raw)
                    parts.append(
                        f"WHEN {self.table_name}.{col} {op} {q_when} "
                        f"THEN {self._quote_if_needed(then_raw)}"
                    )
                    has_when = True

            if not has_when:
                QMessageBox.warning(
                    self,
                    "Ошибка",
                    "Если CASE включён, необходимо добавить хотя бы одно корректное WHEN ... THEN ...\n"
                    "Либо выключите CASE (снимите галочку), чтобы использовать только COALESCE/NULLIF."
                )
                return

            else_val = self.else_edit.text().strip()
            if else_val:
                parts.append(f"ELSE {self._quote_if_needed(else_val)}")
            parts.append("END")
            expr = " ".join(parts)

        # NULLIF применяется первым (внутренняя функция)
        # NULLIF(expr1, expr2) - если expr1 == expr2, возвращает NULL, иначе expr1
        n1 = self.nullif_first_edit.text().strip()
        n2 = self.nullif_second_edit.text().strip()
        if n1 and n2:
            # Если n1 - это имя столбца, используем его напрямую, иначе как значение
            if expr:
                base_for_nullif = expr
            else:
                # Проверяем, является ли n1 именем столбца
                try:
                    cols_info = self.controller.get_table_columns(self.table_name)
                    col_names = [c['name'] for c in cols_info]
                    if n1 in col_names:
                        base_for_nullif = f"{self.table_name}.{n1}"
                    else:
                        # Может быть выражение или значение
                        base_for_nullif = n1 if ('.' in n1 or '(' in n1) else self._quote_if_needed(n1)
                except Exception:
                    # Если не удалось проверить, используем как есть
                    base_for_nullif = n1 if ('.' in n1 or '(' in n1) else self._quote_if_needed(n1)
            expr = f"NULLIF({base_for_nullif}, {self._quote_if_needed(n2)})"

        # COALESCE применяется последним (внешняя функция)
        # COALESCE(expr, default) - возвращает первое не-NULL значение
        coalesce_val = self.coalesce_value_edit.text().strip()
        if coalesce_val:
            if expr:
                base_for_coalesce = expr
            else:
                col = self.coalesce_col_combo.currentText()
                if col:
                    base_for_coalesce = f"{self.table_name}.{col}"
                else:
                    QMessageBox.warning(self, "Ошибка", "Выберите столбец для COALESCE")
                    return
            expr = f"COALESCE({base_for_coalesce}, {self._quote_if_needed(coalesce_val)})"

        if expr is None:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Ничего не задано: включите CASE или заполните COALESCE/NULLIF."
            )
            return

        alias = self.case_alias_edit.text().strip()
        if alias:
            expr = f"{expr} AS {alias}"

        self.final_expr = expr
        self.accept()

    def get_case_expression(self):
        return self.final_expr