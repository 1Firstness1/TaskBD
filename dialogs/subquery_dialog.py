from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QGroupBox, QLineEdit,
    QDialogButtonBox, QLabel, QHBoxLayout, QPushButton
)
from logger import Logger

class SubqueryDialog(QDialog):
    """Диалог подзапросов ANY/ALL/EXISTS (исправленный)."""
    def __init__(self, controller, outer_table, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.outer_table = outer_table
        self.setWindowTitle("Конструктор подзапроса")
        self.setMinimumWidth(620)
        self.clause = ""
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        mode_row = QFormLayout()
        self.mode_combo = QComboBox()
        self.mode_combo.setMinimumWidth(180)
        self.mode_combo.view().setMinimumWidth(210)
        self.mode_combo.addItems(["EXISTS", "ANY", "ALL"])
        mode_row.addRow("Оператор подзапроса:", self.mode_combo)
        layout.addLayout(mode_row)

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

        self.sub_table_combo = QComboBox()
        self.sub_table_combo.setMinimumWidth(220)
        self.sub_table_combo.view().setMinimumWidth(260)
        try:
            all_tables = self.controller.get_all_tables()
            # Добавляем также основную таблицу, если она не в списке
            if self.outer_table and self.outer_table not in all_tables:
                all_tables = [self.outer_table] + all_tables
            self.sub_table_combo.addItems(sorted(set(all_tables)))
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить список таблиц: {str(e)}")
        layout.addWidget(QLabel("Таблица подзапроса:"))
        layout.addWidget(self.sub_table_combo)

        self.sub_col_combo = QComboBox()
        self.sub_col_combo.setMinimumWidth(220)
        self.sub_col_combo.view().setMinimumWidth(260)
        layout.addWidget(QLabel("Столбец подзапроса для выборки (ANY/ALL):"))
        layout.addWidget(self.sub_col_combo)

        layout.addWidget(QLabel("Корреляция (внешний = внутренний):"))
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

        self.filter_value_edit = QLineEdit()
        self.filter_value_edit.setPlaceholderText(
            "Доп. условие по подзапросу (опционально, SQL-фрагмент, например: subq.amount > 0)"
        )
        layout.addWidget(self.filter_value_edit)

        self.mode_combo.currentTextChanged.connect(self._toggle_visibility)
        self.sub_table_combo.currentTextChanged.connect(self._reload_sub_columns)

        self._reload_sub_columns()
        self._toggle_visibility(self.mode_combo.currentText())

        btn_layout = QHBoxLayout()
        build_btn = QPushButton("Добавить условие")
        cancel_btn = QPushButton("Отмена")
        btn_layout.addWidget(build_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        build_btn.clicked.connect(self.build_clause)
        cancel_btn.clicked.connect(self.reject)

    def _reload_sub_columns(self):
        """Перезагрузка столбцов при изменении таблицы подзапроса."""
        table = self.sub_table_combo.currentText()
        if not table:
            return
        try:
            cols = [c['name'] for c in self.controller.get_table_columns(table)]
            self.sub_col_combo.clear()
            self.sub_col_combo.addItems(cols)
            self.where_sub_combo.clear()
            self.where_sub_combo.addItems(cols)
            
            # Обновляем внешние столбцы
            self.where_outer_combo.clear()
            outer_cols = [c['name'] for c in self.controller.get_table_columns(self.outer_table)]
            self.where_outer_combo.addItems(outer_cols)
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить столбцы таблицы: {str(e)}")

    def _toggle_visibility(self, mode):
        is_exists = (mode == "EXISTS")
        self.anyall_group.setEnabled(not is_exists)
        self.sub_col_combo.setEnabled(not is_exists)

    def build_clause(self):
        """Построение SQL-условия с подзапросом."""
        from PySide6.QtWidgets import QMessageBox
        
        mode = self.mode_combo.currentText()
        sub_table = self.sub_table_combo.currentText()
        
        if not sub_table:
            QMessageBox.warning(self, "Ошибка", "Выберите таблицу для подзапроса")
            return
        
        sub_alias = "subq"
        sub_col = self.sub_col_combo.currentText()
        corr_outer = self.where_outer_combo.currentText()
        corr_inner = self.where_sub_combo.currentText()
        
        # Валидация корреляции
        if not corr_outer or not corr_inner:
            QMessageBox.warning(self, "Ошибка", "Выберите столбцы для корреляции (внешний = внутренний)")
            return
        
        extra_where_raw = self.filter_value_edit.text().strip()

        # Формируем WHERE условие для подзапроса
        # Имена столбцов берутся из комбобоксов (безопасно)
        where_parts = [f"{sub_alias}.{corr_inner} = {self.outer_table}.{corr_outer}"]
        if extra_where_raw:
            where_parts.append(extra_where_raw)
        where_clause = " AND ".join(where_parts)

        if mode == "EXISTS":
            self.clause = f"EXISTS (SELECT 1 FROM {sub_table} AS {sub_alias} WHERE {where_clause})"
        else:
            # Для ANY/ALL нужны дополнительные параметры
            if not sub_col:
                QMessageBox.warning(self, "Ошибка", "Выберите столбец для подзапроса (ANY/ALL)")
                return
            outer_col = self.outer_col_combo.currentText()
            if not outer_col:
                QMessageBox.warning(self, "Ошибка", "Выберите внешний столбец для сравнения")
                return
            comp = self.comp_op_combo.currentText()
            self.clause = (
                f"{self.outer_table}.{outer_col} {comp} {mode} "
                f"(SELECT {sub_alias}.{sub_col} FROM {sub_table} AS {sub_alias} WHERE {where_clause})"
            )

        try:
            logger = Logger()
            logger.info(f"Построен подзапрос ({mode}): {self.clause}")
        except Exception:
            pass

        self.accept()

    def get_clause(self):
        return self.clause