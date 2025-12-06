from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QTabWidget, QWidget, QVBoxLayout, QListWidget,
    QFormLayout, QLineEdit, QComboBox, QPushButton, QMessageBox
)

class EnumEditorDialog(QDialog):
    """Окно для редактирования значений ENUM."""
    def __init__(self, controller, type_name, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.type_name = type_name
        self.setWindowTitle(f"ENUM {type_name}")
        self.setMinimumWidth(520)
        self.setMinimumHeight(380)
        self.setup_ui()
        self.refresh_values()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"<b>Тип ENUM: {self.type_name}</b>"))

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        view_tab = QWidget()
        v_layout = QVBoxLayout(view_tab)
        self.values_list = QListWidget()
        v_layout.addWidget(self.values_list)
        self.tabs.addTab(view_tab, "Просмотр")

        add_tab = QWidget()
        a_layout = QFormLayout(add_tab)
        self.new_value_edit = QLineEdit()
        a_layout.addRow("Новое значение:", self.new_value_edit)

        self.pos_combo = QComboBox()
        self.pos_combo.setMinimumWidth(150)
        self.pos_combo.view().setMinimumWidth(180)
        self.pos_combo.addItems(["В конец", "BEFORE", "AFTER"])
        a_layout.addRow("Позиция:", self.pos_combo)

        self.ref_value_edit = QLineEdit()
        self.ref_value_edit.setPlaceholderText("Опорное значение для BEFORE/AFTER")
        a_layout.addRow("Опорное:", self.ref_value_edit)

        add_btn = QPushButton("Добавить значение")
        add_btn.clicked.connect(self.on_add_value)
        a_layout.addRow(add_btn)
        self.tabs.addTab(add_tab, "Добавить")

        ren_tab = QWidget()
        r_layout = QFormLayout(ren_tab)
        self.old_val_edit = QLineEdit()
        self.new_val2_edit = QLineEdit()
        r_layout.addRow("Старое значение:", self.old_val_edit)
        r_layout.addRow("Новое значение:", self.new_val2_edit)
        ren_btn = QPushButton("Переименовать значение")
        ren_btn.clicked.connect(self.on_rename_value)
        r_layout.addRow(ren_btn)
        self.tabs.addTab(ren_tab, "Переименовать")

        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def refresh_values(self):
        vals = self.controller.list_enum_values(self.type_name)
        self.values_list.clear()
        for v in vals:
            self.values_list.addItem(v)

    def on_add_value(self):
        val = self.new_value_edit.text().strip()
        if not val:
            QMessageBox.warning(self, "Ошибка", "Введите значение")
            return
        pos = self.pos_combo.currentText()
        position = pos if pos in ("BEFORE", "AFTER") else None
        ref = self.ref_value_edit.text().strip() if position else None
        ok, msg = self.controller.add_enum_value(self.type_name, val, position, ref)
        if ok:
            QMessageBox.information(self, "Успех", "Значение добавлено")
            self.new_value_edit.clear()
            self.ref_value_edit.clear()
            self.refresh_values()
            self.tabs.setCurrentIndex(0)
        else:
            QMessageBox.critical(self, "Ошибка", msg)

    def on_rename_value(self):
        old_val = self.old_val_edit.text().strip()
        new_val = self.new_val2_edit.text().strip()
        if not old_val or not new_val:
            QMessageBox.warning(self, "Ошибка", "Заполните оба значения")
            return
        ok, msg = self.controller.rename_enum_value(self.type_name, old_val, new_val)
        if ok:
            QMessageBox.information(self, "Успех", "Значение переименовано")
            self.old_val_edit.clear()
            self.new_val2_edit.clear()
            self.refresh_values()
            self.tabs.setCurrentIndex(0)
        else:
            QMessageBox.critical(self, "Ошибка", msg)