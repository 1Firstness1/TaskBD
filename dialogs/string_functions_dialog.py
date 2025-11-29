from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QFormLayout, QComboBox, QLineEdit, QTableWidget,
    QDialogButtonBox, QSpinBox, QPushButton, QMessageBox, QTableWidgetItem
)
from PySide6.QtCore import Qt
from controller import NumericTableItem, DateTableItem, BooleanTableItem, TimestampTableItem
from logger import Logger

class StringFunctionsDialog(QDialog):
    """Диалог работы со строковыми функциями."""
    def __init__(self, controller, table_name, columns_info, parent=None, selected_column=None):
        super().__init__(parent)
        self.controller = controller
        self.table_name = table_name
        self.columns_info = columns_info
        self.selected_column = selected_column
        self.logger = Logger()

        self.setWindowTitle("Строковые функции")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        self.setup_ui()
        self.center_on_screen()

    def center_on_screen(self):
        screen = self.screen().geometry()
        self.move(screen.center() - self.rect().center())

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h3>Применение строковых функций</h3>"))

        form_layout = QFormLayout()

        self.column_combo = QComboBox()
        self.column_combo.setMinimumWidth(200)
        self.column_combo.view().setMinimumWidth(240)
        string_columns = [col['name'] for col in self.columns_info
                          if 'char' in col.get('type', '').lower() or 'text' in col.get('type', '').lower()]
        if not string_columns:
            string_columns = [col['name'] for col in self.columns_info]
        self.column_combo.addItems(string_columns)

        if self.selected_column and self.selected_column in string_columns:
            self.column_combo.setCurrentText(self.selected_column)

        form_layout.addRow("Столбец:", self.column_combo)

        self.function_combo = QComboBox()
        self.function_combo.setMinimumWidth(240)
        self.function_combo.view().setMinimumWidth(280)
        self.function_combo.addItems([
            "UPPER (верхний регистр)",
            "LOWER (нижний регистр)",
            "SUBSTRING (подстрока)",
            "TRIM (удаление пробелов)",
            "LTRIM (удаление пробелов слева)",
            "RTRIM (удаление пробелов справа)",
            "LPAD (дополнение слева)",
            "RPAD (дополнение справа)",
            "CONCAT (объединение)",
            "LENGTH (длина строки)",
            "INITCAP (первый символ в верхнем регистре)"
        ])
        self.function_combo.currentTextChanged.connect(self.on_function_changed)
        form_layout.addRow("Функция:", self.function_combo)

        layout.addLayout(form_layout)

        self.params_widget = QWidget()
        self.params_layout = QFormLayout(self.params_widget)
        layout.addWidget(self.params_widget)

        layout.addWidget(QLabel("<b>Результат:</b>"))
        self.result_table = QTableWidget()
        self.result_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.result_table)

        buttons_layout = QHBoxLayout()
        apply_btn = QPushButton("Применить функцию")
        apply_btn.clicked.connect(self.apply_function)
        buttons_layout.addWidget(apply_btn)

        self.create_column_btn = QPushButton("Создать столбец с результатом")
        self.create_column_btn.clicked.connect(self.create_column_with_function)
        self.create_column_btn.setEnabled(False)
        buttons_layout.addWidget(self.create_column_btn)

        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(close_btn)
        layout.addLayout(buttons_layout)

        self.on_function_changed(self.function_combo.currentText())

    def on_function_changed(self, function_text):
        while self.params_layout.rowCount() > 0:
            self.params_layout.removeRow(0)

        if "SUBSTRING" in function_text:
            self.start_pos = QSpinBox()
            self.start_pos.setRange(1, 1000)
            self.start_pos.setValue(1)
            self.params_layout.addRow("Начальная позиция:", self.start_pos)

            self.length = QSpinBox()
            self.length.setRange(1, 1000)
            self.length.setValue(10)
            self.params_layout.addRow("Длина:", self.length)

        elif "LPAD" in function_text or "RPAD" in function_text:
            self.pad_length = QSpinBox()
            self.pad_length.setRange(1, 1000)
            self.pad_length.setValue(20)
            self.params_layout.addRow("Длина:", self.pad_length)

            self.pad_char = QLineEdit()
            self.pad_char.setText(" ")
            self.pad_char.setMaxLength(1)
            self.params_layout.addRow("Символ:", self.pad_char)

        elif "CONCAT" in function_text:
            self.concat_text = QLineEdit()
            self.concat_text.setPlaceholderText("Текст для объединения")
            self.params_layout.addRow("Текст:", self.concat_text)

            self.concat_position = QComboBox()
            self.concat_position.setMinimumWidth(140)
            self.concat_position.view().setMinimumWidth(170)
            self.concat_position.addItems(["В начале", "В конце"])
            self.params_layout.addRow("Позиция:", self.concat_position)

        self.current_function = function_text

    def get_sql_expression(self):
        column = self.column_combo.currentText()
        function = self.function_combo.currentText()

        try:
            if "UPPER" in function:
                sql_expr = f"upper(\"{column}\")"
            elif "LOWER" in function:
                sql_expr = f"lower(\"{column}\")"
            elif "INITCAP" in function:
                sql_expr = f"initcap(\"{column}\")"
            elif "SUBSTRING" in function:
                start = self.start_pos.value()
                length = self.length.value()
                sql_expr = f"substring(\"{column}\" FROM {start} FOR {length})"
            elif "LTRIM" in function:
                sql_expr = f"ltrim(\"{column}\")"
            elif "RTRIM" in function:
                sql_expr = f"rtrim(\"{column}\")"
            elif "TRIM" in function:
                sql_expr = f"trim(\"{column}\")"
            elif "LPAD" in function:
                length = self.pad_length.value()
                char = self.pad_char.text() or ' '
                sql_expr = f"lpad(\"{column}\", {length}, '{char}')"
            elif "RPAD" in function:
                length = self.pad_length.value()
                char = self.pad_char.text() or ' '
                sql_expr = f"rpad(\"{column}\", {length}, '{char}')"
            elif "CONCAT" in function:
                text = self.concat_text.text()
                if self.concat_position.currentText() == "В начале":
                    sql_expr = f"concat('{text}', \"{column}\")"
                else:
                    sql_expr = f"concat(\"{column}\", '{text}')"
            elif "LENGTH" in function:
                sql_expr = f"length(\"{column}\")"
            else:
                raise ValueError("Неизвестная функция")

            return sql_expr, column
        except Exception as e:
            self.logger.error(f"Ошибка формирования SQL выражения: {str(e)}")
            return None, None

    def apply_function(self):
        try:
            sql_expr, column = self.get_sql_expression()
            if not sql_expr:
                QMessageBox.warning(self, "Ошибка", "Не удалось сформировать SQL выражение")
                return

            query = f"SELECT {column} as original, {sql_expr} as result FROM \"{self.table_name}\" LIMIT 20"
            results = self.controller.execute_select(query)

            if results:
                self.result_table.setColumnCount(2)
                self.result_table.setHorizontalHeaderLabels(["Оригинал", "Результат"])
                self.result_table.setRowCount(len(results))

                from datetime import datetime as _dt, date as _date
                for row_idx, row_data in enumerate(results):
                    for col_idx, value in enumerate(row_data):
                        if value is None:
                            item = QTableWidgetItem("NULL")
                            item.setForeground(Qt.gray)
                        else:
                            str_value = str(value)
                            if isinstance(value, (int, float)):
                                item = NumericTableItem(str_value, value)
                            elif isinstance(value, _date):
                                item = DateTableItem(str_value, value)
                            elif isinstance(value, _dt):
                                item = TimestampTableItem(str_value, value)
                            elif isinstance(value, bool):
                                item = BooleanTableItem(str_value, value)
                            else:
                                item = QTableWidgetItem(str_value)
                        self.result_table.setItem(row_idx, col_idx, item)

                self.result_table.resizeColumnsToContents()
                self.logger.info(f"Функция {self.function_combo.currentText()} применена успешно")
                self.create_column_btn.setEnabled(True)
            else:
                QMessageBox.information(self, "Результат", "Нет данных для отображения")

        except Exception as e:
            self.logger.error(f"Ошибка применения функции: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Ошибка при применении функции:\n{str(e)}")

    def create_column_with_function(self):
        try:
            sql_expr, orig_column = self.get_sql_expression()
            if not sql_expr:
                QMessageBox.warning(self, "Ошибка", "Не удалось сформировать SQL выражение")
                return

            function_name = self.current_function.split(" ")[0].lower()
            suggested_name = f"{function_name}_{orig_column}"

            new_column_name, ok = QInputDialog.getText(
                self, "Имя нового столбца",
                "Введите имя для нового столбца:",
                text=suggested_name
            )

            if not ok or not new_column_name:
                return

            data_type = "TEXT"
            if "LENGTH" in self.current_function:
                data_type = "INTEGER"

            success, error = self.controller.add_column(
                self.table_name, new_column_name, data_type
            )

            if not success:
                QMessageBox.critical(self, "Ошибка", f"Не удалось добавить столбец:\n{error}")
                return

            update_query = f"UPDATE \"{self.table_name}\" SET \"{new_column_name}\" = {sql_expr}"
            success, error = self.controller.execute_update(update_query)

            if success:
                QMessageBox.information(
                    self,
                    "Успех",
                    f"Столбец '{new_column_name}' успешно создан и заполнен результатами функции."
                )
                self.logger.info(f"Создан столбец '{new_column_name}' с функцией {self.current_function}")
                self.accept()
                if hasattr(self.parent(), 'accept'):
                    self.parent().accept()
            else:
                self.controller.drop_column(self.table_name, new_column_name)
                QMessageBox.critical(self, "Ошибка", f"Ошибка при заполнении столбца:\n{error}")
                self.logger.error(f"Ошибка при заполнении столбца '{new_column_name}': {error}")

        except Exception as e:
            self.logger.error(f"Ошибка создания столбца: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Ошибка при создании столбца:\n{str(e)}")