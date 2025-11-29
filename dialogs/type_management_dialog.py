from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QGroupBox,
    QFormLayout, QLineEdit, QPushButton, QComboBox, QMessageBox,
    QScrollArea, QWidget
)
from PySide6.QtCore import Qt
from .enum_editor_dialog import EnumEditorDialog
from .composite_editor_dialog import CompositeEditorDialog

class TypeManagementDialog(QDialog):
    """
    Диалог управления типами данных:
    - слева список типов (ENUM и составные)
    - справа подсказки
    - снизу компактный и не ломающийся блок создания нового типа (ENUM или составной)
    """
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.setWindowTitle("Типы данных")
        self.setMinimumWidth(820)
        self.setMinimumHeight(540)
        self.setup_ui()
        self.refresh_types()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Показать:"))
        self.type_filter_combo = QComboBox()
        self.type_filter_combo.setMinimumWidth(160)
        self.type_filter_combo.view().setMinimumWidth(200)
        self.type_filter_combo.addItems(["Все", "ENUM", "Составные"])
        filter_layout.addWidget(self.type_filter_combo)
        filter_layout.addStretch()
        main_layout.addLayout(filter_layout)

        center_layout = QHBoxLayout()
        self.types_list = QListWidget()
        self.types_list.setMinimumWidth(260)
        center_layout.addWidget(self.types_list, 2)

        self.hint_label = QLabel(
            "<b>Советы:</b><br>"
            "• Двойной клик по ENUM — редактирование значений<br>"
            "• Двойной клик по составному типу — редактирование атрибутов"
        )
        self.hint_label.setWordWrap(True)
        center_layout.addWidget(self.hint_label, 1)
        main_layout.addLayout(center_layout, stretch=2)

        main_layout.addSpacing(4)

        new_group = QGroupBox("Создание нового типа")
        new_group_layout = QVBoxLayout(new_group)
        new_group_layout.setContentsMargins(10, 8, 10, 8)
        new_group_layout.setSpacing(6)

        top_form = QFormLayout()
        top_form.setHorizontalSpacing(12)
        top_form.setVerticalSpacing(4)

        self.new_type_kind = QComboBox()
        self.new_type_kind.setMinimumWidth(130)
        self.new_type_kind.view().setMinimumWidth(170)
        self.new_type_kind.addItems(["ENUM", "Составной"])
        top_form.addRow("Тип:", self.new_type_kind)

        self.new_type_name = QLineEdit()
        self.new_type_name.setPlaceholderText("Имя типа (идентификатор)")
        top_form.addRow("Имя:", self.new_type_name)

        new_group_layout.addLayout(top_form)

        self.enum_group = QGroupBox("Значения ENUM")
        enum_layout = QVBoxLayout(self.enum_group)
        enum_layout.setContentsMargins(8, 4, 8, 4)
        self.new_enum_values = QLineEdit()
        self.new_enum_values.setPlaceholderText("low,medium,high")
        enum_layout.addWidget(self.new_enum_values)
        new_group_layout.addWidget(self.enum_group)

        self.composite_group = QGroupBox("Поля составного типа")
        self.composite_group.setMinimumHeight(120)
        comp_layout = QVBoxLayout(self.composite_group)
        comp_layout.setContentsMargins(8, 4, 8, 4)
        comp_layout.setSpacing(4)

        # Создаем область прокрутки для полей
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setMinimumHeight(150)
        scroll_area.setMaximumHeight(300)
        
        # Виджет-контейнер для полей
        fields_widget = QWidget()
        self.comp_fields_layout = QVBoxLayout(fields_widget)
        self.comp_fields_layout.setContentsMargins(0, 0, 0, 0)
        self.comp_fields_layout.setSpacing(4)
        self.comp_fields_layout.addStretch()  # Добавляем растяжку внизу
        
        scroll_area.setWidget(fields_widget)
        comp_layout.addWidget(scroll_area)

        # Панель управления полями
        fields_control_layout = QHBoxLayout()
        fields_control_layout.addStretch()
        
        # Кнопка добавления одного поля
        add_field_btn = QPushButton("Добавить поле")
        add_field_btn.setFixedWidth(130)
        add_field_btn.clicked.connect(self.add_composite_field_row)
        fields_control_layout.addWidget(add_field_btn)
        
        comp_layout.addLayout(fields_control_layout)

        new_group_layout.addWidget(self.composite_group)

        self.create_type_btn = QPushButton("Создать тип")
        self.create_type_btn.setMinimumHeight(32)
        new_group_layout.addWidget(self.create_type_btn)

        new_hint = QLabel(
            "<i>Подсказка для составного типа:</i><br>"
            "• Введите имя поля и выберите тип данных из списка.<br>"
            "• При большом количестве полей диалог можно растянуть по вертикали."
        )
        new_hint.setWordWrap(True)
        new_group_layout.addWidget(new_hint)

        main_layout.addWidget(new_group, stretch=3)

        btn_bar = QHBoxLayout()
        self.refresh_btn = QPushButton("Обновить")
        self.delete_btn = QPushButton("Удалить выбранный тип")
        close_btn = QPushButton("Закрыть")
        btn_bar.addWidget(self.refresh_btn)
        btn_bar.addWidget(self.delete_btn)
        btn_bar.addStretch()
        btn_bar.addWidget(close_btn)
        main_layout.addLayout(btn_bar)

        self.type_filter_combo.currentTextChanged.connect(self.refresh_types)
        self.types_list.itemDoubleClicked.connect(self.open_type_editor)
        self.create_type_btn.clicked.connect(self.create_type)
        self.refresh_btn.clicked.connect(self.refresh_types)
        self.delete_btn.clicked.connect(self.delete_selected_type)
        close_btn.clicked.connect(self.accept)
        self.new_type_kind.currentTextChanged.connect(self._toggle_kind_ui)

        self._toggle_kind_ui(self.new_type_kind.currentText())
        self._init_composite_fields()

    def _toggle_kind_ui(self, kind_text: str):
        """Переключение между ENUM и Составным типом."""
        is_comp = (kind_text == "Составной")
        self.enum_group.setVisible(not is_comp)
        self.composite_group.setVisible(is_comp)
        # При переключении на составной тип инициализируем поля
        if is_comp:
            self._init_composite_fields()

    def _init_composite_fields(self):
        """Очистка и инициализация полей составного типа."""
        while self.comp_fields_layout.count():
            item = self.comp_fields_layout.takeAt(0)
            lay = item.layout()
            if lay:
                while lay.count():
                    witem = lay.takeAt(0)
                    w = witem.widget()
                    if w:
                        w.setParent(None)
                        w.deleteLater()
            elif item.spacerItem():
                # Пропускаем растяжку
                del item
                continue
            del item
        # Создаем одно поле
        self.add_composite_field_row()

    def add_composite_field_row(self):
        """Добавляет новую строку поля в составной тип."""
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        from PySide6.QtWidgets import QLineEdit, QComboBox, QPushButton

        name_edit = QLineEdit()
        name_edit.setPlaceholderText("имя_поля")
        name_edit.setMinimumWidth(180)

        type_combo = QComboBox()
        type_combo.setMinimumWidth(160)
        type_combo.view().setMinimumWidth(220)
        type_combo.addItems([
            "INTEGER", "BIGINT", "NUMERIC", "TEXT",
            "VARCHAR(100)", "VARCHAR(200)",
            "BOOLEAN", "DATE", "TIMESTAMP"
        ])
        type_combo.setEditable(True)

        remove_btn = QPushButton("−")
        remove_btn.setFixedWidth(26)
        remove_btn.setToolTip("Удалить поле")

        def remove_row():
            for w in (name_edit, type_combo, remove_btn):
                w.setParent(None)
                w.deleteLater()
            idx = -1
            # Ищем индекс строки, исключая растяжку в конце
            for i in range(self.comp_fields_layout.count()):
                item = self.comp_fields_layout.itemAt(i)
                if item and item.layout() is row:
                    idx = i
                    break
            if idx >= 0:
                # Временно удаляем растяжку
                last_item = self.comp_fields_layout.takeAt(self.comp_fields_layout.count() - 1)
                if last_item and last_item.spacerItem():
                    del last_item
                
                # Удаляем строку
                item = self.comp_fields_layout.takeAt(idx)
                del item
                
                # Возвращаем растяжку
                self.comp_fields_layout.addStretch()

        remove_btn.clicked.connect(remove_row)

        from PySide6.QtWidgets import QLabel
        row.addWidget(QLabel("Имя:"))
        row.addWidget(name_edit, stretch=2)
        row.addWidget(QLabel("Тип:"))
        row.addWidget(type_combo, stretch=1)
        row.addWidget(remove_btn, stretch=0, alignment=Qt.AlignRight)

        # Удаляем растяжку перед добавлением нового поля
        if self.comp_fields_layout.count() > 0:
            last_item = self.comp_fields_layout.itemAt(self.comp_fields_layout.count() - 1)
            if last_item and last_item.spacerItem():
                self.comp_fields_layout.removeItem(last_item)
        
        self.comp_fields_layout.addLayout(row)
        # Добавляем растяжку обратно в конец
        self.comp_fields_layout.addStretch()

    def refresh_types(self):
        self.types_list.clear()
        filter_kind = self.type_filter_combo.currentText()
        enum_types = self.controller.list_enum_types()
        comp_types = self.controller.list_composite_types()

        if filter_kind in ("Все", "ENUM"):
            for t in enum_types:
                self.types_list.addItem(f"ENUM: {t}")
        if filter_kind in ("Все", "Составные"):
            for t in comp_types:
                self.types_list.addItem(f"COMPOSITE: {t}")

    def parse_selected_type(self):
        item = self.types_list.currentItem()
        if not item:
            return None, None
        text = item.text()
        if text.startswith("ENUM: "):
            return "ENUM", text.split("ENUM: ", 1)[1]
        if text.startswith("COMPOSITE: "):
            return "COMPOSITE", text.split("COMPOSITE: ", 1)[1]
        return None, None

    def open_type_editor(self, item):
        kind, name = self.parse_selected_type()
        if not kind or not name:
            return
        if kind == "ENUM":
            dlg = EnumEditorDialog(self.controller, name, self)
        else:
            dlg = CompositeEditorDialog(self.controller, name, self)
        dlg.exec_()
        self.refresh_types()

    def create_type(self):
        kind = self.new_type_kind.currentText()
        name = self.new_type_name.text().strip()
        if not name:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Ошибка", "Укажите имя типа")
            return

        from PySide6.QtWidgets import QMessageBox
        if kind == "ENUM":
            raw_vals = self.new_enum_values.text().strip()
            if not raw_vals:
                QMessageBox.warning(self, "Ошибка", "Укажите значения ENUM через запятую")
                return
            values = [v.strip() for v in raw_vals.split(",") if v.strip()]
            ok, msg = self.controller.create_enum_type(name, values)
            if ok:
                QMessageBox.information(self, "Успех", f"ENUM {name} создан.")
                self.new_type_name.clear()
                self.new_enum_values.clear()
                self.refresh_types()
            else:
                QMessageBox.critical(self, "Ошибка", msg)
        else:
            # Создание составного типа
            cols = []
            # Игнорируем последний элемент (растяжку)
            for i in range(self.comp_fields_layout.count() - 1):
                item = self.comp_fields_layout.itemAt(i)
                row = item.layout()
                if not row:
                    continue
                name_edit = None
                type_combo = None
                for j in range(row.count()):
                    w = row.itemAt(j).widget()
                    from PySide6.QtWidgets import QLineEdit, QComboBox
                    if isinstance(w, QLineEdit) and not name_edit:
                        name_edit = w
                    elif isinstance(w, QComboBox) and not type_combo:
                        type_combo = w
                if not name_edit or not type_combo:
                    continue
                cname = name_edit.text().strip()
                ctype = type_combo.currentText().strip()
                if cname and ctype:
                    cols.append((cname, ctype))

            if not cols:
                QMessageBox.warning(self, "Ошибка", "Добавьте хотя бы одно поле составного типа")
                return

            ok, msg = self.controller.create_composite_type(name, cols)
            if ok:
                QMessageBox.information(self, "Успех", f"Составной тип {name} создан.")
                self.new_type_name.clear()
                self._init_composite_fields()
                self.refresh_types()
            else:
                QMessageBox.critical(self, "Ошибка", msg)

    def delete_selected_type(self):
        kind, name = self.parse_selected_type()
        from PySide6.QtWidgets import QMessageBox
        if not name:
            QMessageBox.warning(self, "Ошибка", "Выберите тип в списке")
            return
        if QMessageBox.question(
            self, "Удаление типа", f"Удалить тип {name}? (операция необратима)",
            QMessageBox.Yes | QMessageBox.No
        ) != QMessageBox.Yes:
            return
        ok, msg = self.controller.drop_type(name)
        if ok:
            QMessageBox.information(self, "Успех", f"Тип {name} удалён.")
            self.refresh_types()
        else:
            QMessageBox.critical(self, "Ошибка", msg)