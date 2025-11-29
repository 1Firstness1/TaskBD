from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel

class DeleteColumnDialog(QDialog):
    """Диалог для удаления столбца (оставлен для совместимости)."""
    def __init__(self, controller, table_name, columns_info, selected_column=None, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.table_name = table_name
        self.columns_info = columns_info
        self.selected_column = selected_column

        self.setWindowTitle("Удалить столбец")
        self.setMinimumWidth(300)
        self.setup_ui()
        self.center_on_screen()

    def center_on_screen(self):
        screen = self.screen().geometry()
        self.move(screen.center() - self.rect().center())

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Для удаления столбца используйте кнопку в предыдущем окне."))