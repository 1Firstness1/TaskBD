from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QGroupBox, QLineEdit,
    QDialogButtonBox, QLabel, QHBoxLayout, QPushButton, QMessageBox, QCheckBox
)
from logger import Logger

class SubqueryDialog(QDialog):
    """Диалог подзапросов ANY/ALL/EXISTS с управлением корреляцией."""
    def __init__(self, controller, outer_table, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.outer_table = outer_table
        self.setWindowTitle("Конструктор подзапроса")
        self.setMinimumWidth(640)
        self.clause = ""
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

        mode_row = QFormLayout()
        self.mode_combo = QComboBox()
        self.mode_combo.setMinimumWidth(180)
        self.mode_combo.view().setMinimumWidth(210)
        self.mode_combo.addItems(["EXISTS", "ANY", "ALL"])
        mode_row.addRow("Оператор подзапроса:", self.mode_combo)
        layout.addLayout(mode_row)

        # Параметры ANY/ALL
        self.anyall_group = QGroupBox("Параметры для ANY/ALL")
        anyall_layout = QFormLayout(self.anyall_group)

        self.outer_col_combo = QComboBox()
        self.outer_col_combo.setMinimumWidth(180)
        self.outer_col_combo.view().setMinimumWidth(210)
        outer_cols = [c['name'] for c in self.controller.get_table_columns(self.outer_table)]
        self.outer_col_combo.addItems(outer_cols)
        anyall_layout.addRow("Внешний столбец:", self.outer_col_combo)

        self.comp_op_combo = QComboBox()
        self.comp_op_combo.setMinimumWidth(120)
        self.comp_op_combo.view().setMinimumWidth(150)
        self.comp_op_combo.addItems(["=", "!=", ">", "<", ">=", "<="])
        anyall_layout.addRow("Оператор сравнения:", self.comp_op_combo)
        layout.addWidget(self.anyall_group)

        # Таблица и столбец подзапроса
        self.sub_table_combo = QComboBox()
        self.sub_table_combo.setMinimumWidth(220)
        self.sub_table_combo.view().setMinimumWidth(260)
        try:
            all_tables = self.controller.get_all_tables()
            if self.outer_table and self.outer_table not in all_tables:
                all_tables = [self.outer_table] + all_tables
            self.sub_table_combo.addItems(sorted(set(all_tables)))
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить список таблиц: {str(e)}")
        layout.addWidget(QLabel("Таблица подзапроса:"))
        layout.addWidget(self.sub_table_combo)

        self.sub_col_combo = QComboBox()
        self.sub_col_combo.setMinimumWidth(220)
        self.sub_col_combo.view().setMinimumWidth(260)
        layout.addWidget(QLabel("Столбец подзапроса для выборки (ANY/ALL):"))
        layout.addWidget(self.sub_col_combo)

        # Корреляция: управляемая чекбоксом
        self.use_corr_check = QCheckBox("Использовать корреляцию (внешний = внутренний)")
        self.use_corr_check.setChecked(False)  # по умолчанию отключено
        self.use_corr_check.setStyleSheet(checkbox_style)
        layout.addWidget(self.use_corr_check)

        corr_layout = QHBoxLayout()
        self.where_outer_combo = QComboBox()
        self.where_outer_combo.setMinimumWidth(180)
        self.where_outer_combo.view().setMinimumWidth(210)
        self.where_sub_combo = QComboBox()
        self.where_sub_combo.setMinimumWidth(180)
        self.where_sub_combo.view().setMinimumWidth(210)
        corr_layout.addWidget(self.where_outer_combo)
        corr_layout.addWidget(QLabel("="))
        corr_layout.addWidget(self.where_sub_combo)
        layout.addLayout(corr_layout)

        # Доп. условие
        self.filter_value_edit = QLineEdit()
        self.filter_value_edit.setPlaceholderText(
            "Доп. условие для подзапроса (опционально). Пример: subq.amount > 0"
        )
        layout.addWidget(self.filter_value_edit)

        self.mode_combo.currentTextChanged.connect(self._toggle_visibility)
        self.sub_table_combo.currentTextChanged.connect(self._reload_sub_columns)
        self.use_corr_check.stateChanged.connect(self._toggle_corr_controls)

        self._reload_sub_columns()
        self._toggle_visibility(self.mode_combo.currentText())
        self._toggle_corr_controls()  # применить состояние чекбокса

        btn_layout = QHBoxLayout()
        build_btn = QPushButton("Добавить условие")
        cancel_btn = QPushButton("Отмена")
        btn_layout.addWidget(build_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        build_btn.clicked.connect(self.build_clause)
        cancel_btn.clicked.connect(self.reject)

    def _reload_sub_columns(self):
        table = self.sub_table_combo.currentText()
        if not table:
            return
        try:
            cols = [c['name'] for c in self.controller.get_table_columns(table)]
            self.sub_col_combo.clear()
            self.sub_col_combo.addItems(cols)
            self.where_sub_combo.clear()
            self.where_sub_combo.addItems(cols)

            self.where_outer_combo.clear()
            outer_cols = [c['name'] for c in self.controller.get_table_columns(self.outer_table)]
            self.where_outer_combo.addItems(outer_cols)
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить столбцы таблицы: {str(e)}")

    def _toggle_visibility(self, mode):
        is_exists = (mode == "EXISTS")
        # В EXISTS параметры ANY/ALL не нужны
        self.anyall_group.setEnabled(not is_exists)
        self.sub_col_combo.setEnabled(not is_exists)
        # В EXISTS корреляция по умолчанию включена (чаще всего нужна)
        if is_exists:
            self.use_corr_check.setChecked(True)
        else:
            # Для ANY/ALL по умолчанию выключаем корреляцию
            self.use_corr_check.setChecked(False)
        self._toggle_corr_controls()

    def _toggle_corr_controls(self):
        enabled = self.use_corr_check.isChecked()
        self.where_outer_combo.setEnabled(enabled)
        self.where_sub_combo.setEnabled(enabled)

    def _is_safe_extra_where(self, text: str) -> bool:
        bad_tokens = [';', 'DROP ', 'DELETE ', 'ALTER ', 'TRUNCATE ', 'INSERT ', 'UPDATE ']
        t = text.upper()
        return not any(tok in t for tok in bad_tokens)

    def _types_compatible(self, table_a, col_a, table_b, col_b) -> bool:
        try:
            a = next((c for c in self.controller.get_table_columns(table_a) if c['name'] == col_a), None)
            b = next((c for c in self.controller.get_table_columns(table_b) if c['name'] == col_b), None)
            if not a or not b:
                return True
            ta = a.get('type', '').lower()
            tb = b.get('type', '').lower()
            if ta == tb:
                return True
            groups = [
                ('int', 'int'), ('numeric', 'numeric'), ('decimal', 'decimal'),
                ('real', 'real'), ('double', 'double'), ('char', 'char'),
                ('text', 'text'), ('date', 'date'), ('timestamp', 'timestamp'), ('bool', 'bool')
            ]
            for ga, gb in groups:
                if (ga in ta and gb in tb) or (gb in ta and ga in tb):
                    return True
            return False
        except Exception:
            return True

    def build_clause(self):
        mode = self.mode_combo.currentText()
        sub_table = self.sub_table_combo.currentText()
        if not sub_table:
            QMessageBox.warning(self, "Ошибка", "Выберите таблицу для подзапроса")
            return

        sub_alias = "subq"
        sub_col = self.sub_col_combo.currentText()
        extra_where_raw = self.filter_value_edit.text().strip()
        if extra_where_raw and not self._is_safe_extra_where(extra_where_raw):
            QMessageBox.warning(self, "Ошибка", "Дополнительное условие содержит недопустимые конструкции")
            return

        # Собираем WHERE для подзапроса
        where_parts = []
        # Корреляция включается только если чекбокс активен
        if self.use_corr_check.isChecked():
            corr_outer = self.where_outer_combo.currentText()
            corr_inner = self.where_sub_combo.currentText()
            if not corr_outer or not corr_inner:
                QMessageBox.warning(self, "Ошибка", "Выберите столбцы для корреляции (внешний = внутренний)")
                return
            where_parts.append(f"{sub_alias}.{corr_inner} = {self.outer_table}.{corr_outer}")

        if extra_where_raw:
            where_parts.append(extra_where_raw)
        where_clause = " AND ".join(where_parts) if where_parts else ""

        if mode == "EXISTS":
            if where_clause == "":
                QMessageBox.information(
                    self, "Подсказка",
                    "EXISTS обычно используется с корреляцией или доп.условием, иначе он вернёт все строки."
                )
            inner_where = f" WHERE {where_clause}" if where_clause else ""
            self.clause = f"EXISTS (SELECT 1 FROM {sub_table} AS {sub_alias}{inner_where})"
        else:
            # ANY/ALL
            if not sub_col:
                QMessageBox.warning(self, "Ошибка", "Выберите столбец для подзапроса (ANY/ALL)")
                return
            outer_col = self.outer_col_combo.currentText()
            if not outer_col:
                QMessageBox.warning(self, "Ошибка", "Выберите внешний столбец для сравнения")
                return

            # Предупреждение, если пользователь включил корреляцию и выбрал одинаковый столбец
            if self.use_corr_check.isChecked() and outer_col == sub_col:
                QMessageBox.information(
                    self, "Предупреждение",
                    "Корреляция по тому же столбцу, что участвует в сравнении ANY/ALL, часто даёт пустой результат.\n"
                    "Рекомендуется отключить корреляцию для ANY/ALL."
                )

            if not self._types_compatible(self.outer_table, outer_col, sub_table, sub_col):
                QMessageBox.information(
                    self, "Предупреждение",
                    "Типы внешнего и внутреннего столбцов могут быть несовместимы. Проверьте корректность сравнения."
                )

            comp = self.comp_op_combo.currentText()
            inner_where = f" WHERE {where_clause}" if where_clause else ""
            self.clause = (
                f"{self.outer_table}.{outer_col} {comp} {mode} "
                f"(SELECT {sub_alias}.{sub_col} FROM {sub_table} AS {sub_alias}{inner_where})"
            )

        try:
            Logger().info(f"Построен подзапрос ({mode}): {self.clause}")
        except Exception:
            pass

        self.accept()

    def get_clause(self):
        return self.clause