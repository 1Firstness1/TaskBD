from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QDialogButtonBox
)

class SortDialog(QDialog):
    """Диалог сортировки по столбцу."""
    def __init__(self, column, parent=None):
        super().__init__(parent)
        self.column = column
        self.direction = "ASC"
        self.setWindowTitle(f"Сортировка: {self.column}")
        self.setMinimumWidth(180)
        self.setup_ui()
        self.center_on_screen()

    def center_on_screen(self):
        screen = self.screen().geometry()
        self.move(screen.center() - self.rect().center())

    def setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.dir_combo = QComboBox()
        self.dir_combo.setMinimumWidth(120)
        self.dir_combo.view().setMinimumWidth(150)
        self.dir_combo.addItems(["ASC", "DESC"])
        form.addRow("Направление:", self.dir_combo)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_dialog)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept_dialog(self):
        self.direction = self.dir_combo.currentText()
        self.accept()