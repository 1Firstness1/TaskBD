from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QFormLayout, QComboBox, QLineEdit,
    QGroupBox, QDialogButtonBox, QCheckBox, QMessageBox
)

class SearchDialog(QDialog):
    """Диалог поиска по таблице с защитой от SQL Injection и SIMILAR TO."""
    def __init__(self, controller, table_name, columns_info, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.table_name = table_name
        self.columns_info = columns_info
        self.search_condition = None
        self.search_params = []
        self.setWindowTitle("Поиск")
        self.setMinimumWidth(500)
        self.setup_ui()
        self.center_on_screen()

    def center_on_screen(self):
        screen = self.screen().geometry()
        self.move(screen.center() - self.rect().center())

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h3>Поиск по таблице</h3>"))

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

        form_layout = QFormLayout()
        self.column_combo = QComboBox()
        self.column_combo.setMinimumWidth(200)
        self.column_combo.view().setMinimumWidth(250)
        self.column_combo.addItems([col['name'] for col in self.columns_info])
        form_layout.addRow("Столбец:", self.column_combo)

        self.search_type_combo = QComboBox()
        self.search_type_combo.setMinimumWidth(220)
        self.search_type_combo.view().setMinimumWidth(260)
        self.search_type_combo.addItems([
            "LIKE (шаблонный поиск)",
            "~ (регулярка)",
            "~* (регулярка без учета регистра)",
            "!~ (не соответствует)",
            "!~* (не соответствует без учета регистра)",
            "= (точное совпадение)"
        ])
        form_layout.addRow("Тип поиска:", self.search_type_combo)

        self.search_text = QLineEdit()
        self.search_text.setPlaceholderText("Введите текст для поиска...")
        form_layout.addRow("Текст:", self.search_text)
        layout.addLayout(form_layout)

        hint_label = QLabel(
            "<i><b>Подсказка:</b><br>"
            "• LIKE: используйте % (пример: %текст%)<br>"
            "• ~: POSIX регулярное выражение<br>"
            "• ~*: регулярка без учета регистра</i>"
        )
        hint_label.setWordWrap(True)
        layout.addWidget(hint_label)

        self.regex_group = QGroupBox("SIMILAR TO")
        regex_layout = QVBoxLayout(self.regex_group)
        self.regex_column_combo = QComboBox()
        self.regex_column_combo.setMinimumWidth(200)
        self.regex_column_combo.view().setMinimumWidth(250)
        self.regex_pattern_edit = QLineEdit()
        self.regex_pattern_edit.setPlaceholderText("Шаблон (например: '(Р|Г)%')")
        self.regex_not_checkbox = QCheckBox("NOT SIMILAR TO")
        self.regex_not_checkbox.setStyleSheet(checkbox_style)

        cols = [c['name'] for c in self.controller.get_table_columns(self.table_name)]
        self.regex_column_combo.addItems(cols)
        regex_layout.addWidget(QLabel("Столбец"))
        regex_layout.addWidget(self.regex_column_combo)
        regex_layout.addWidget(QLabel("Шаблон"))
        regex_layout.addWidget(self.regex_pattern_edit)
        regex_layout.addWidget(self.regex_not_checkbox)
        layout.addWidget(self.regex_group)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_dialog)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept_dialog(self):
        pattern = self.regex_pattern_edit.text().strip()
        if pattern:
            col = self.regex_column_combo.currentText()
            not_part = "NOT " if self.regex_not_checkbox.isChecked() else ""
            # Используем параметризацию для защиты от SQL injection
            self.search_condition = f"{col} {not_part}SIMILAR TO %s"
            self.search_params = [pattern]
            self.accept()
            return

        column = self.column_combo.currentText()
        search_text = self.search_text.text().strip()
        if not search_text:
            QMessageBox.warning(self, "Ошибка", "Введите текст для поиска или заполните блок SIMILAR TO")
            return

        st = self.search_type_combo.currentText()
        if "LIKE" in st:
            self.search_condition = f"{column} LIKE %s"
            self.search_params = [f"%{search_text}%"]
        elif "~*" in st and "!" in st:
            self.search_condition = f"{column} !~* %s"
            self.search_params = [search_text]
        elif "~*" in st:
            self.search_condition = f"{column} ~* %s"
            self.search_params = [search_text]
        elif "!~" in st:
            self.search_condition = f"{column} !~ %s"
            self.search_params = [search_text]
        elif "~" in st:
            self.search_condition = f"{column} ~ %s"
            self.search_params = [search_text]
        else:
            self.search_condition = f"{column} = %s"
            self.search_params = [search_text]

        self.accept()