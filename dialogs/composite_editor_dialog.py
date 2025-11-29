from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QListWidget, QGroupBox,
    QFormLayout, QLineEdit, QHBoxLayout, QPushButton, QMessageBox
)

class CompositeEditorDialog(QDialog):
    """Редактор атрибутов составного типа."""
    def __init__(self, controller, type_name, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.type_name = type_name
        self.setWindowTitle(f"Составной тип {type_name}")
        self.setMinimumWidth(550)
        self.setup_ui()
        self.refresh_attrs()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"<b>Атрибуты типа {self.type_name}</b>"))
        self.attrs_list = QListWidget()
        layout.addWidget(self.attrs_list)

        add_group = QGroupBox("Добавить атрибут")
        add_form = QFormLayout(add_group)
        self.add_name = QLineEdit()
        self.add_type = QLineEdit()
        self.add_type.setPlaceholderText("INTEGER, TEXT, my_enum и т.д.")
        add_form.addRow("Имя:", self.add_name)
        add_form.addRow("Тип:", self.add_type)

        del_group = QGroupBox("Удалить атрибут")
        del_form = QFormLayout(del_group)
        self.del_name = QLineEdit()
        del_form.addRow("Имя:", self.del_name)

        ren_group = QGroupBox("Переименовать атрибут")
        ren_form = QFormLayout(ren_group)
        self.ren_old = QLineEdit()
        self.ren_new = QLineEdit()
        ren_form.addRow("Старое имя:", self.ren_old)
        ren_form.addRow("Новое имя:", self.ren_new)

        alt_group = QGroupBox("Изменить тип атрибута")
        alt_form = QFormLayout(alt_group)
        self.alt_name = QLineEdit()
        self.alt_type = QLineEdit()
        alt_form.addRow("Имя:", self.alt_name)
        alt_form.addRow("Новый тип:", self.alt_type)

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(add_group)
        actions_layout.addWidget(del_group)
        actions_layout.addWidget(ren_group)
        actions_layout.addWidget(alt_group)
        layout.addLayout(actions_layout)

        btn_bar = QHBoxLayout()
        add_btn = QPushButton("Добавить")
        del_btn = QPushButton("Удалить")
        ren_btn = QPushButton("Переименовать")
        alt_btn = QPushButton("Изменить тип")
        close_btn = QPushButton("Закрыть")
        btn_bar.addWidget(add_btn)
        btn_bar.addWidget(del_btn)
        btn_bar.addWidget(ren_btn)
        btn_bar.addWidget(alt_btn)
        btn_bar.addStretch()
        btn_bar.addWidget(close_btn)
        layout.addLayout(btn_bar)

        add_btn.clicked.connect(self.on_add_attr)
        del_btn.clicked.connect(self.on_del_attr)
        ren_btn.clicked.connect(self.on_rename_attr)
        alt_btn.clicked.connect(self.on_alt_type)
        close_btn.clicked.connect(self.accept)

    def refresh_attrs(self):
        attrs = self.controller.list_composite_attributes(self.type_name)
        self.attrs_list.clear()
        for name, typ in attrs:
            self.attrs_list.addItem(f"{name}: {typ}")

    def on_add_attr(self):
        name = self.add_name.text().strip()
        typ = self.add_type.text().strip()
        if not name or not typ:
            QMessageBox.warning(self, "Ошибка", "Заполните имя и тип")
            return
        ok, msg = self.controller.composite_add_attribute(self.type_name, name, typ)
        if ok:
            QMessageBox.information(self, "Успех", "Атрибут добавлен")
            self.add_name.clear()
            self.add_type.clear()
            self.refresh_attrs()
        else:
            QMessageBox.critical(self, "Ошибка", msg)

    def on_del_attr(self):
        name = self.del_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Укажите имя атрибута")
            return
        ok, msg = self.controller.composite_drop_attribute(self.type_name, name)
        if ok:
            QMessageBox.information(self, "Успех", "Атрибут удалён")
            self.del_name.clear()
            self.refresh_attrs()
        else:
            QMessageBox.critical(self, "Ошибка", msg)

    def on_rename_attr(self):
        old = self.ren_old.text().strip()
        new = self.ren_new.text().strip()
        if not old or not new:
            QMessageBox.warning(self, "Ошибка", "Заполните старое и новое имена")
            return
        ok, msg = self.controller.composite_rename_attribute(self.type_name, old, new)
        if ok:
            QMessageBox.information(self, "Успех", "Атрибут переименован")
            self.ren_old.clear()
            self.ren_new.clear()
            self.refresh_attrs()
        else:
            QMessageBox.critical(self, "Ошибка", msg)

    def on_alt_type(self):
        name = self.alt_name.text().strip()
        typ = self.alt_type.text().strip()
        if not name or not typ:
            QMessageBox.warning(self, "Ошибка", "Заполните имя и новый тип")
            return
        ok, msg = self.controller.composite_alter_attribute_type(self.type_name, name, typ)
        if ok:
            QMessageBox.information(self, "Успех", "Тип атрибута изменён")
            self.alt_name.clear()
            self.alt_type.clear()
            self.refresh_attrs()
        else:
            QMessageBox.critical(self, "Ошибка", msg)