from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QDialogButtonBox, QMessageBox
)

from .edit_column_dialog import EditColumnDialog
from .edit_record_dialog import EditRecordDialog

class EditMenuDialog(QDialog):
    """Диалог меню редактирования."""
    def __init__(self, controller, table_name, columns_info, data_table, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.table_name = table_name
        self.columns_info = columns_info
        self.data_table = data_table
        self.action_taken = False

        self.setWindowTitle("Редактировать")
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

        edit_column_btn = QPushButton("Редактировать столбец")
        edit_column_btn.setMinimumHeight(50)
        edit_column_btn.clicked.connect(self.edit_column)
        layout.addWidget(edit_column_btn)

        edit_record_btn = QPushButton("Редактировать запись")
        edit_record_btn.setMinimumHeight(50)
        edit_record_btn.clicked.connect(self.edit_record)
        layout.addWidget(edit_record_btn)

        layout.addStretch()

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_dialog)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def edit_column(self):
        selected_column = None
        selected_items = self.data_table.selectedItems()
        if selected_items:
            selected_col_idx = self.data_table.column(selected_items[0])
            column_name = self.data_table.horizontalHeaderItem(selected_col_idx).text()
            if column_name:
                selected_column = column_name

        if not selected_column:
            QMessageBox.warning(self, "Ошибка", "Выберите ячейку столбца, который хотите редактировать")
            return

        dialog = EditColumnDialog(self.controller, self.table_name, self.columns_info, selected_column, self)
        if dialog.exec_():
            self.action_taken = True
            self.accept()

    def edit_record(self):
        if not self.data_table.rowCount():
            QMessageBox.warning(self, "Ошибка", "Таблица пуста, нечего редактировать")
            return

        selected_items = self.data_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Ошибка", "Выберите ячейку в записи для редактирования")
            return

        item = selected_items[0]
        row = item.row()

        if row < 0 or row >= self.data_table.rowCount():
            QMessageBox.warning(self, "Ошибка", "Неверная строка")
            return

        row_data = {}
        for col_idx in range(self.data_table.columnCount()):
            cell_item = self.data_table.item(row, col_idx)
            if cell_item:
                col_name = self.data_table.horizontalHeaderItem(col_idx).text()
                row_data[col_name] = cell_item.text()

        dialog = EditRecordDialog(self.controller, self.table_name, self.columns_info, row_data, self)
        if dialog.exec_():
            self.action_taken = True
            self.accept()

    def accept_dialog(self):
        self.accept()