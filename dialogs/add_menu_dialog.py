from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QDialogButtonBox
)
from .add_column_dialog import AddColumnDialog
from .add_record_dialog import AddRecordDialog

class AddMenuDialog(QDialog):
    """Диалог меню добавления."""
    def __init__(self, controller, table_name, columns_info, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.table_name = table_name
        self.columns_info = columns_info
        self.action_taken = False

        self.setWindowTitle("Добавить")
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

        add_column_btn = QPushButton("Создать столбец")
        add_column_btn.setMinimumHeight(50)
        add_column_btn.clicked.connect(self.add_column)
        layout.addWidget(add_column_btn)

        add_record_btn = QPushButton("Создать запись")
        add_record_btn.setMinimumHeight(50)
        add_record_btn.clicked.connect(self.add_record)
        layout.addWidget(add_record_btn)

        layout.addStretch()

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_dialog)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def add_column(self):
        # Извлекаем пользовательские типы без явного isinstance, чтобы избежать циклического импорта:
        # Получаем пользовательские типы из task_dialog или напрямую из контроллера
        task_dialog = self.parent()
        if hasattr(task_dialog, 'all_user_types'):
            user_types = task_dialog.all_user_types
        else:
            # Если task_dialog недоступен, получаем типы напрямую
            try:
                enum_types = self.controller.list_enum_types()
                comp_types = self.controller.list_composite_types()
                user_types = list(enum_types) + list(comp_types)
            except Exception:
                user_types = []
        dialog = AddColumnDialog(self.controller, self.table_name, user_types, self)
        if dialog.exec_():
            self.action_taken = True
            self.accept()

    def add_record(self):
        dialog = AddRecordDialog(self.controller, self.table_name, self.columns_info, self)
        if dialog.exec_():
            self.action_taken = True
            self.accept()

    def accept_dialog(self):
        self.accept()