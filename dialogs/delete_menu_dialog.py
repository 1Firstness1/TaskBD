from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QDialogButtonBox, QMessageBox
)

class DeleteMenuDialog(QDialog):
    """Диалог меню удаления."""
    def __init__(self, controller, table_name, columns_info, data_table, selected_column=None, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.table_name = table_name
        self.columns_info = columns_info
        self.data_table = data_table
        self.selected_column = selected_column
        self.action_taken = False

        self.setWindowTitle("Удалить")
        self.setMinimumWidth(400)
        self.setMinimumHeight(250)
        self.setup_ui()
        self.center_on_screen()

    def center_on_screen(self):
        screen = self.screen().geometry()
        self.move(screen.center() - self.rect().center())

    def setup_ui(self):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("<h3>Выберите действие</h3>"))

        delete_column_btn = QPushButton("Удалить столбец")
        delete_column_btn.setMinimumHeight(50)
        delete_column_btn.clicked.connect(self.delete_column)
        layout.addWidget(delete_column_btn)

        delete_record_btn = QPushButton("Удалить запись")
        delete_record_btn.setMinimumHeight(50)
        delete_record_btn.clicked.connect(self.delete_record)
        layout.addWidget(delete_record_btn)

        layout.addStretch()

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_dialog)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def delete_column(self):
        column_to_delete = self.selected_column
        if not column_to_delete:
            selected_items = self.data_table.selectedItems()
            if selected_items:
                selected_col_idx = self.data_table.column(selected_items[0])
                header_item = self.data_table.horizontalHeaderItem(selected_col_idx)
                if header_item:
                    column_to_delete = header_item.text()

        if not column_to_delete:
            QMessageBox.warning(self, "Ошибка", "Выберите ячейку столбца, который хотите удалить")
            return

        confirm = QMessageBox.question(
            self,
            "Подтверждение",
            f"Вы уверены, что хотите удалить столбец '{column_to_delete}'?\nЭто действие необратимо!",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm != QMessageBox.Yes:
            return

        success, error = self.controller.drop_column(self.table_name, column_to_delete)
        if success:
            QMessageBox.information(self, "Успех", f"Столбец '{column_to_delete}' удален")
            self.action_taken = True
            self.accept()
        else:
            QMessageBox.critical(self, "Ошибка", f"Не удалось удалить столбец:\n{error}")

    def delete_record(self):
        if not self.data_table.rowCount():
            QMessageBox.warning(self, "Ошибка", "Таблица пуста, нечего удалять")
            return

        selected_items = self.data_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Ошибка", "Выберите ячейку в записи для удаления")
            return

        item = selected_items[0]
        row = item.row()

        if row < 0 or row >= self.data_table.rowCount():
            QMessageBox.warning(self, "Ошибка", "Неверная строка")
            return

        confirm = QMessageBox.question(
            self,
            "Подтверждение",
            "Вы уверены, что хотите удалить эту запись?",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm != QMessageBox.Yes:
            return

        if not self.data_table.columnCount():
            QMessageBox.warning(self, "Ошибка", "Нет данных для удаления")
            return

        first_col_item = self.data_table.horizontalHeaderItem(0)
        if not first_col_item:
            return
        first_col = first_col_item.text()
        first_value_item = self.data_table.item(row, 0)
        first_value = first_value_item.text() if first_value_item else None

        where_clause = f"{first_col} = %s"
        success, error = self.controller.delete_row(self.table_name, where_clause, [first_value])

        if success:
            QMessageBox.information(self, "Успех", "Запись успешно удалена")
            self.action_taken = True
            self.accept()
        else:
            QMessageBox.critical(self, "Ошибка", f"Не удалось удалить запись:\n{error}")

    def accept_dialog(self):
        self.accept()