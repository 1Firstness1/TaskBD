from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QComboBox, QGroupBox, QScrollArea, QWidget,
    QVBoxLayout, QHBoxLayout, QCheckBox, QDialogButtonBox
)
from PySide6.QtCore import Qt

class JoinWizardDialog(QDialog):
    """Мастер создания JOIN запросов."""
    def __init__(self, controller, base_table, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.base_table = base_table
        self.scroll_area = None
        self.join_columns_checks = {}
        self.base_columns_checks = {}

        self.setWindowTitle("Мастер соединений (JOIN)")
        self.setMinimumWidth(780)
        self.setMinimumHeight(600)
        self.setup_ui()
        self.center_on_screen()

    def center_on_screen(self):
        screen = self.screen().geometry()
        self.move(screen.center() - self.rect().center())

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"<h3>Создание JOIN запроса</h3>"))
        layout.addWidget(QLabel(f"<b>Базовая таблица:</b> {self.base_table}"))

        layout.addWidget(QLabel("<b>Выберите таблицу для соединения:</b>"))

        join_table_layout = QHBoxLayout()
        join_table_layout.addWidget(QLabel("Таблица:"))

        self.join_table_combo = QComboBox()
        self.join_table_combo.setMinimumWidth(200)
        self.join_table_combo.view().setMinimumWidth(240)
        all_tables = self.controller.get_all_tables()
        other_tables = [t for t in all_tables if t != self.base_table]
        self.join_table_combo.addItems(other_tables)
        join_table_layout.addWidget(self.join_table_combo)
        layout.addLayout(join_table_layout)

        join_type_layout = QHBoxLayout()
        join_type_layout.addWidget(QLabel("Тип соединения:"))
        self.join_type_combo = QComboBox()
        self.join_type_combo.setMinimumWidth(140)
        self.join_type_combo.view().setMinimumWidth(180)
        self.join_type_combo.addItems(["INNER", "LEFT", "RIGHT", "FULL"])
        join_type_layout.addWidget(self.join_type_combo)
        layout.addLayout(join_type_layout)

        layout.addWidget(QLabel("<b>Условие соединения (ON):</b>"))

        on_layout = QHBoxLayout()
        self.base_column_combo = QComboBox()
        self.base_column_combo.setMinimumWidth(160)
        self.base_column_combo.view().setMinimumWidth(200)
        self.update_base_columns()
        on_layout.addWidget(QLabel(f"{self.base_table}."))
        on_layout.addWidget(self.base_column_combo)

        on_layout.addWidget(QLabel(" = "))

        self.join_column_combo = QComboBox()
        self.join_column_combo.setMinimumWidth(160)
        self.join_column_combo.view().setMinimumWidth(200)
        self.join_table_label = QLabel()
        on_layout.addWidget(self.join_table_label)
        on_layout.addWidget(QLabel("."))
        on_layout.addWidget(self.join_column_combo)

        layout.addLayout(on_layout)

        layout.addWidget(QLabel("<b>Выберите столбцы для вывода:</b>"))

        columns_layout = QHBoxLayout()

        checkbox_style = """
        QCheckBox {
            color: white;
        }
        QCheckBox::indicator {
            width: 14px; height: 14px;
            border: 1px solid #c0c0c0; border-radius: 3px; background: white;
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
        self.checkbox_style = checkbox_style

        # базовая таблица
        base_group = QGroupBox(f"Столбцы таблицы {self.base_table}")
        base_layout = QVBoxLayout(base_group)
        base_scroll = QScrollArea()
        base_scroll.setWidgetResizable(True)
        base_scroll_widget = QWidget()
        base_scroll_layout = QVBoxLayout(base_scroll_widget)

        self.base_columns_checks = {}
        base_columns = self.controller.get_table_columns(self.base_table) or []
        for col in base_columns:
            check = QCheckBox(f"{col['name']}", parent=base_scroll_widget)
            check.setChecked(True)
            check.setLayoutDirection(Qt.LeftToRight)
            check.setStyleSheet(self.checkbox_style)
            self.base_columns_checks[col['name']] = check
            base_scroll_layout.addWidget(check)

        base_scroll_layout.addStretch()
        base_scroll.setWidget(base_scroll_widget)
        base_layout.addWidget(base_scroll)
        columns_layout.addWidget(base_group)

        # присоединяемая таблица
        join_group = QGroupBox("Столбцы присоединяемой таблицы")
        join_layout = QVBoxLayout(join_group)

        self.join_scroll = QScrollArea()
        self.join_scroll.setWidgetResizable(True)
        self.join_scroll_widget = QWidget()
        self.join_scroll_layout = QVBoxLayout(self.join_scroll_widget)
        self.join_scroll.setWidget(self.join_scroll_widget)
        join_layout.addWidget(self.join_scroll)
        columns_layout.addWidget(join_group)

        self.join_columns_checks = {}
        self.join_table_combo.currentTextChanged.connect(self._populate_join_checkboxes)
        self._populate_join_checkboxes(self.join_table_combo.currentText())

        layout.addLayout(columns_layout)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _clear_layout_safe(self, vlayout):
        if vlayout is None:
            return
        while vlayout.count():
            item = vlayout.takeAt(vlayout.count() - 1)
            if item is None:
                continue
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
            child_layout = item.layout()
            if child_layout is not None:
                self._clear_layout_safe(child_layout)

    def _populate_join_checkboxes(self, table_name):
        if not hasattr(self, "join_scroll_layout") or self.join_scroll_layout is None:
            return

        self._clear_layout_safe(self.join_scroll_layout)
        self.join_columns_checks = {}

        if not table_name:
            self.join_table_label.setText("")
            self.join_column_combo.clear()
            return

        self.join_table_label.setText(table_name)
        join_columns = self.controller.get_table_columns(table_name) or []

        for col in join_columns:
            check = QCheckBox(f"{col['name']}", parent=self.join_scroll_widget)
            check.setChecked(True)
            check.setLayoutDirection(Qt.LeftToRight)
            check.setStyleSheet(self.checkbox_style)
            self.join_columns_checks[col['name']] = check
            self.join_scroll_layout.addWidget(check)

        self.join_scroll_layout.addStretch()

        cur = self.join_column_combo.currentText()
        self.join_column_combo.blockSignals(True)
        self.join_column_combo.clear()
        for col in join_columns:
            self.join_column_combo.addItem(col['name'])
        if cur and cur in [c['name'] for c in join_columns]:
            self.join_column_combo.setCurrentText(cur)
        self.join_column_combo.blockSignals(False)

    def update_base_columns(self):
        columns = self.controller.get_table_columns(self.base_table)
        self.base_column_combo.clear()
        self.base_column_combo.addItems([col['name'] for col in columns])

    def get_join_config(self):
        join_table = self.join_table_combo.currentText()
        join_type = self.join_type_combo.currentText()

        base_col = self.base_column_combo.currentText()
        join_col = self.join_column_combo.currentText()
        on_condition = f"{self.base_table}.{base_col} = {join_table}.{join_col}"

        selected_columns = []
        column_labels = []
        column_mapping = {}

        for col_name, check in self.base_columns_checks.items():
            if check.isChecked():
                full_column_name = f"{self.base_table}.{col_name}"
                display_name = f"{self.base_table}_{col_name}"
                selected_columns.append(full_column_name)
                column_labels.append(display_name)
                column_mapping[display_name] = full_column_name

        for col_name, check in self.join_columns_checks.items():
            if check.isChecked():
                full_column_name = f"{join_table}.{col_name}"
                display_name = f"{join_table}_{col_name}"
                selected_columns.append(full_column_name)
                column_labels.append(display_name)
                column_mapping[display_name] = full_column_name

        if not selected_columns:
            selected_columns = [f"{self.base_table}.*", f"{join_table}.*"]
            base_columns = [col['name'] for col in self.controller.get_table_columns(self.base_table)]
            join_columns = [col['name'] for col in self.controller.get_table_columns(join_table)]
            column_labels = []
            for col in base_columns:
                display_name = f"{self.base_table}_{col}"
                column_labels.append(display_name)
                column_mapping[display_name] = f"{self.base_table}.{col}"
            for col in join_columns:
                display_name = f"{join_table}_{col}"
                column_labels.append(display_name)
                column_mapping[display_name] = f"{join_table}.{col}"

        return {
            'tables_info': [{'name': self.base_table, 'alias': None}],
            'selected_columns': selected_columns,
            'column_labels': column_labels,
            'column_mapping': column_mapping,
            'join_conditions': [
                {
                    'type': join_type,
                    'table': join_table,
                    'alias': None,
                    'on': on_condition
                }
            ],
            'where': None,
            'order_by': None
        }