from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QInputDialog, QMessageBox
)

class EditColumnDialog(QDialog):
    """Диалог редактирования столбца."""
    def __init__(self, controller, table_name, columns_info, selected_column=None, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.table_name = table_name
        self.columns_info = columns_info
        self.selected_column = selected_column

        self.setWindowTitle("Редактировать столбец")
        self.setMinimumWidth(450)
        self.setup_ui()
        self.center_on_screen()

    def center_on_screen(self):
        screen = self.screen().geometry()
        self.move(screen.center() - self.rect().center())

    def setup_ui(self):
        layout = QVBoxLayout(self)

        info_text = self.selected_column if self.selected_column else "не выбран"
        layout.addWidget(QLabel(f"Выбранный столбец: <b>{info_text}</b>"))

        layout.addWidget(QLabel("<b>Выберите операцию:</b>"))

        rename_btn = QPushButton("Переименовать столбец")
        rename_btn.clicked.connect(self.rename_column)
        layout.addWidget(rename_btn)

        change_type_btn = QPushButton("Изменить тип данных")
        change_type_btn.clicked.connect(self.change_column_type)
        layout.addWidget(change_type_btn)

        set_constraint_btn = QPushButton("Установить ограничение")
        set_constraint_btn.clicked.connect(self.set_constraint)
        layout.addWidget(set_constraint_btn)

        drop_constraint_btn = QPushButton("Снять ограничение")
        drop_constraint_btn.clicked.connect(self.drop_constraint)
        layout.addWidget(drop_constraint_btn)

        layout.addStretch()

        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def get_current_column(self):
        return self.selected_column

    def _ensure_column_selected(self):
        if not self.selected_column:
            QMessageBox.warning(self, "Ошибка", "Выберите ячейку столбца, который хотите редактировать")
            return False
        return True

    def rename_column(self):
        if not self._ensure_column_selected():
            return
        old_name = self.get_current_column()
        new_name, ok = QInputDialog.getText(
            self, "Переименование столбца",
            f"Новое имя для столбца '{old_name}':",
            text=old_name
        )

        if ok and new_name and new_name != old_name:
            success, error = self.controller.rename_column(self.table_name, old_name, new_name)
            if success:
                QMessageBox.information(self, "Успех", f"Столбец переименован: {old_name} → {new_name}")
                for col in self.columns_info:
                    if col['name'] == old_name:
                        col['name'] = new_name
                        break
                self.selected_column = new_name
            else:
                QMessageBox.critical(self, "Ошибка", f"Не удалось переименовать столбец:\n{error}")

    def change_column_type(self):
        if not self._ensure_column_selected():
            return
        column = self.get_current_column()

        try:
            enum_types = self.controller.list_enum_types()
        except Exception:
            enum_types = []
        try:
            comp_types = self.controller.list_composite_types()
        except Exception:
            comp_types = []
        user_types = enum_types + comp_types

        types = [
            "INTEGER", "BIGINT", "VARCHAR(100)", "VARCHAR(200)",
            "TEXT", "BOOLEAN", "DATE", "TIMESTAMP", "NUMERIC"
        ]
        if user_types:
            types.append("---------- пользовательские ----------")
            types.extend(user_types)

        new_type, ok = QInputDialog.getItem(
            self, "Изменение типа",
            f"Новый тип для столбца '{column}':",
            types, 0, False
        )

        if not ok or not new_type:
            return

        if "----------" in new_type:
            QMessageBox.warning(self, "Ошибка", "Выберите конкретный тип данных")
            return

        success, error = self.controller.alter_column_type(self.table_name, column, new_type)
        if success:
            QMessageBox.information(self, "Успех", f"Тип столбца '{column}' изменен на {new_type}")
        else:
            QMessageBox.critical(self, "Ошибка", f"Не удалось изменить тип столбца:\n{error}")

    def set_constraint(self):
        column = self.get_current_column()
        if not self._ensure_column_selected():
            return

        from PySide6.QtWidgets import QInputDialog
        constraints = ["NOT NULL", "UNIQUE", "CHECK", "FOREIGN KEY"]
        constraint, ok = QInputDialog.getItem(
            self, "Установка ограничения",
            f"Выберите тип ограничения для '{column}':",
            constraints, 0, False
        )
        if not ok:
            return

        constraint_value = None
        ref_table = None
        ref_column = None

        if constraint == "CHECK":
            constraint_value, ok = QInputDialog.getText(
                self, "Условие CHECK",
                f"Введите условие CHECK для '{column}':\n(например: {column} > 0)"
            )
            if not ok or not constraint_value:
                return
        elif constraint == "FOREIGN KEY":
            ref_table, ok = QInputDialog.getText(
                self, "FOREIGN KEY - таблица",
                "Введите имя связанной таблицы (REFERENCES table):"
            )
            if not ok or not ref_table:
                return
            ref_column, ok = QInputDialog.getText(
                self, "FOREIGN KEY - столбец",
                "Введите имя связанного столбца (REFERENCES table(column)):"
            )
            if not ok or not ref_column:
                return

        if constraint == "FOREIGN KEY":
            param = (ref_table, ref_column)
        else:
            param = constraint_value

        success, error = self.controller.set_constraint(
            self.table_name, column, constraint, param
        )

        if success:
            QMessageBox.information(self, "Успех",
                                    f"Ограничение {constraint} установлено на столбец '{column}'")
        else:
            QMessageBox.critical(self, "Ошибка", f"Не удалось установить ограничение:\n{error}")

    def drop_constraint(self):
        column = self.get_current_column()
        if not self._ensure_column_selected():
            return

        from PySide6.QtWidgets import QInputDialog
        constraints = ["NOT NULL", "UNIQUE", "CHECK", "FOREIGN KEY"]
        constraint, ok = QInputDialog.getItem(
            self, "Снятие ограничения",
            f"Выберите тип ограничения для снятия с '{column}':",
            constraints, 0, False
        )
        if not ok:
            return

        success, error = self.controller.drop_constraint(self.table_name, column, constraint)
        if success:
            QMessageBox.information(self, "Успех",
                                    f"Ограничение {constraint} снято со столбца '{column}'")
        else:
            QMessageBox.critical(self, "Ошибка", f"Не удалось снять ограничение:\n{error}")