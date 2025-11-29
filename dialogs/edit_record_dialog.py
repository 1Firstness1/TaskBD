from PySide6.QtWidgets import (
    QDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QPushButton, QSpinBox,
    QDoubleSpinBox, QCheckBox, QDateEdit, QTimeEdit, QLineEdit, QMessageBox, QComboBox
)
from PySide6.QtCore import QDate, QTime
from controller import ValidatedLineEdit
from datetime import datetime, date

class EditRecordDialog(QDialog):
    """Диалог редактирования записи с поддержкой составных типов."""
    def __init__(self, controller, table_name, columns_info, current_data, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.table_name = table_name
        self.columns_info = columns_info
        self.current_data = current_data
        self.field_widgets = {}

        self.setWindowTitle("Редактировать запись")
        self.setMinimumWidth(500)
        self.setup_ui()
        self.center_on_screen()

    def center_on_screen(self):
        screen = self.screen().geometry()
        self.move(screen.center() - self.rect().center())

    @staticmethod
    def _is_composite_type(col_type: str) -> bool:
        t = col_type.lower()
        base_keywords = [
            "int", "serial", "numeric", "decimal", "real", "double",
            "bool", "char", "text", "date", "time", "timestamp",
            "json", "jsonb", "uuid", "array", "[]"
        ]
        return not any(k in t for k in base_keywords)

    def _get_composite_attributes(self, type_name: str):
        try:
            return self.controller.list_composite_attributes(type_name)
        except Exception:
            return []
    
    def _get_existing_composite_values(self, col_name: str, type_name: str):
        """Получает существующие значения составного типа из таблицы."""
        try:
            # Получаем все уникальные значения этого столбца
            query = f'SELECT DISTINCT "{col_name}" FROM "{self.table_name}" WHERE "{col_name}" IS NOT NULL'
            results = self.controller.execute_select(query)
            values = []
            for row in results:
                val = row.get(col_name) if isinstance(row, dict) else row[0]
                if val is not None:
                    values.append(str(val))
            return values
        except Exception as e:
            return []
    
    def _is_enum_type(self, col_type: str) -> bool:
        """Проверяет, является ли тип ENUM."""
        # Проверяем, есть ли этот тип в списке ENUM типов
        try:
            enum_types = self.controller.list_enum_types()
            return col_type in enum_types
        except Exception:
            return False

    def setup_ui(self):
        layout = QFormLayout(self)
        label_style = "color: #333333; font-weight: bold;"

        first_col_name = self.columns_info[0]['name']

        for col in self.columns_info:
            col_name = col['name']
            col_type = col.get('type', '')
            col_type_lower = col_type.lower()
            is_nullable = col.get('nullable', True)

            label = QLabel(f"{col_name}:")
            label.setStyleSheet(label_style)
            if not is_nullable:
                label.setText(f"{col_name} *")

            if self._is_composite_type(col_type):
                group = QGroupBox(f"{col_name} ({col_type})")
                group_layout = QFormLayout(group)

                attrs = self._get_composite_attributes(col_type)
                raw_value = self.current_data.get(col_name)
                
                # Выпадающий список с существующими значениями
                value_combo = QComboBox()
                value_combo.setStyleSheet("""
                    QComboBox {
                        background-color: white;
                        color: #333333;
                        border: 1px solid #c0c0c0;
                        padding: 4px;
                        min-width: 200px;
                        border-radius: 4px;
                    }
                    QComboBox:focus {
                        border: 1px solid #4a86e8;
                    }
                """)
                
                # Получаем существующие значения
                existing_values = self._get_existing_composite_values(col_name, col_type)
                value_combo.addItem("-- Выберите значение --", None)
                for val in existing_values:
                    value_combo.addItem(val, val)
                value_combo.addItem("-- Создать новое значение --", "__new__")
                
                # Устанавливаем текущее значение, если оно есть
                if raw_value:
                    val_str = str(raw_value)
                    index = value_combo.findData(val_str)
                    if index >= 0:
                        value_combo.setCurrentIndex(index)
                    else:
                        # Если значение не найдено в списке, добавляем его
                        value_combo.insertItem(1, val_str, val_str)
                        value_combo.setCurrentIndex(1)
                
                # Форма для создания нового значения
                new_value_group = QGroupBox("Новое значение")
                new_value_group.setVisible(False)
                new_value_layout = QFormLayout(new_value_group)
                
                attr_widgets = {}
                if attrs:
                    for attr_name, attr_type in attrs:
                        attr_label = QLabel(attr_name + ":")
                        attr_label.setStyleSheet("color: #333333;")
                        w = self.create_widget_for_type(attr_type.lower(), {"name": attr_name, "type": attr_type})
                        attr_widgets[attr_name] = w
                        new_value_layout.addRow(attr_label, w)
                else:
                    w = ValidatedLineEdit(self.controller)
                    w.setPlaceholderText("Значение составного типа (RAW)")
                    attr_widgets["__raw__"] = w
                    new_value_layout.addRow(QLabel("Значение:"), w)
                
                # Обработчик изменения выбора
                def on_combo_changed(index):
                    data = value_combo.itemData(index)
                    if data == "__new__":
                        new_value_group.setVisible(True)
                        # Очищаем поля
                        for w in attr_widgets.values():
                            if hasattr(w, 'clear'):
                                w.clear()
                            elif hasattr(w, 'setText'):
                                w.setText('')
                    else:
                        new_value_group.setVisible(False)
                
                value_combo.currentIndexChanged.connect(on_combo_changed)
                
                group_layout.addRow(QLabel("Выберите значение:"), value_combo)
                group_layout.addRow(new_value_group)

                self.field_widgets[col_name] = {
                    "type_name": col_type,
                    "attrs": attrs,
                    "widgets": attr_widgets,
                    "value_combo": value_combo,
                    "new_value_group": new_value_group
                }

                # Если текущее значение не в списке, показываем форму для редактирования
                if raw_value:
                    val_str = str(raw_value)
                    if val_str not in existing_values:
                        value_combo.setCurrentIndex(value_combo.count() - 1)  # "Создать новое значение"
                        self._set_composite_widget_value(col_type, attr_widgets, attrs, raw_value)

                if col_name == first_col_name:
                    group.setEnabled(False)

                layout.addRow(label, group)
            else:
                widget = self.create_widget_for_type(col_type_lower, col)
                self.field_widgets[col_name] = widget

                if col_name in self.current_data:
                    self.set_widget_value(widget, self.current_data[col_name], col_type)

                if col_name == first_col_name:
                    if hasattr(widget, 'setReadOnly'):
                        widget.setReadOnly(True)
                        widget.setStyleSheet("background-color: #f0f0f0;")
                    elif hasattr(widget, 'setEnabled'):
                        widget.setEnabled(False)
                        widget.setStyleSheet("background-color: #f0f0f0;")

                layout.addRow(label, widget)

        buttons_layout = QHBoxLayout()
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self.validate_and_accept)
        buttons_layout.addWidget(save_btn)
        layout.addRow("", buttons_layout)

    def create_widget_for_type(self, col_type, col_info):
        blue = "#4a86e8"
        blue_hover = "#3a76d8"
        blue_dark = "#2a66c8"

        spin_style = f"""
        QSpinBox, QDoubleSpinBox, QTimeEdit, QDateEdit {{
            background-color: white;
            color: #333333;
            border: 1px solid #c0c0c0;
            border-radius: 4px;
            padding: 4px 6px;
            min-height: 25px;
        }}
        QSpinBox:focus, QDoubleSpinBox:focus, QTimeEdit:focus, QDateEdit:focus {{
            border: 1px solid {blue};
        }}
        """

        checkbox_style = f"""
        QCheckBox {{
            color: #333333;
        }}
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border: 1px solid #c0c0c0;
            border-radius: 3px;
            background: white;
        }}
        QCheckBox::indicator:hover {{
            border: 1px solid {blue_hover};
            background: #f0f6ff;
        }}
        QCheckBox::indicator:checked {{
            background-color: {blue};
            border: 1px solid {blue_dark};
            image: none;
        }}
        """

        if 'int' in col_type or 'serial' in col_type:
            w = QSpinBox()
            w.setRange(-2147483648, 2147483647)
            w.setStyleSheet(spin_style)
            return w
        if any(t in col_type for t in ['numeric', 'decimal', 'real', 'double']):
            w = QDoubleSpinBox()
            w.setRange(-999999999.99, 999999999.99)
            w.setDecimals(2)
            w.setStyleSheet(spin_style)
            return w
        if 'bool' in col_type:
            w = QCheckBox()
            w.setStyleSheet(checkbox_style)
            return w
        if 'date' in col_type and 'timestamp' not in col_type:
            w = QDateEdit()
            w.setCalendarPopup(True)
            w.setStyleSheet(spin_style)
            return w
        if 'timestamp' in col_type:
            w = QDateEdit()
            w.setCalendarPopup(True)
            w.setStyleSheet(spin_style)
            return w
        if 'time' in col_type:
            w = QTimeEdit()
            w.setStyleSheet(spin_style)
            return w
        # Проверка ENUM типов
        if self._is_enum_type(col_info.get('type', '')):
            w = QComboBox()
            try:
                enum_values = self.controller.list_enum_values(col_info.get('type', ''))
                w.addItems(enum_values)
                w.setStyleSheet(f"""
                    QComboBox {{
                        background-color: white;
                        color: #333333;
                        border: 1px solid #c0c0c0;
                        padding: 4px;
                        min-width: 120px;
                        border-radius: 4px;
                    }}
                    QComboBox:focus {{
                        border: 1px solid {blue};
                    }}
                    QComboBox::drop-down {{
                        border: none;
                        width: 20px;
                    }}
                """)
            except Exception:
                # Если не удалось получить значения, используем обычное поле
                w = ValidatedLineEdit(self.controller)
            return w
        
        if any(t in col_type for t in ['text', 'varchar', 'char']):
            w = ValidatedLineEdit(self.controller)
            w.setStyleSheet(f"""
                QLineEdit {{
                    background-color: white;
                    color: #333333;
                    border: 1px solid #c0c0c0;
                    padding: 4px;
                    min-width: 120px;
                    border-radius: 4px;
                }}
                QLineEdit:focus {{
                    border: 1px solid {blue};
                }}
            """)
            return w

        w = ValidatedLineEdit(self.controller)
        w.setStyleSheet(f"""
            QLineEdit {{
                background-color: white;
                color: #333333;
                border: 1px solid #c0c0c0;
                padding: 4px;
                min-width: 120px;
                border-radius: 4px;
            }}
            QLineEdit:focus {{
                border: 1px solid {blue};
            }}
        """)
        return w

    def _set_composite_widget_value(self, type_name: str, widgets: dict, attrs: list, raw_value):
        if raw_value is None:
            return

        if not attrs and "__raw__" in widgets:
            if hasattr(widgets["__raw__"], "setText"):
                widgets["__raw__"].setText(str(raw_value))
            return

        s = str(raw_value).strip()
        if s.startswith("(") and s.endswith(")"):
            inner = s[1:-1]
            parts = [p.strip() for p in inner.split(",")]
        else:
            parts = [s]

        for (attr_name, attr_type), val in zip(attrs, parts):
            w = widgets.get(attr_name)
            if not w:
                continue
            if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            self.set_widget_value(w, val, attr_type)

    def set_widget_value(self, widget, value, col_type):
        if value is None:
            return
        try:
            if isinstance(widget, QSpinBox):
                widget.setValue(int(value))
            elif isinstance(widget, QDoubleSpinBox):
                widget.setValue(float(value))
            elif isinstance(widget, QCheckBox):
                widget.setChecked(bool(value))
            elif isinstance(widget, QComboBox):
                # Устанавливаем значение ENUM в комбобокс
                value_str = str(value)
                index = widget.findText(value_str)
                if index >= 0:
                    widget.setCurrentIndex(index)
                else:
                    # Если значение не найдено, добавляем его
                    widget.addItem(value_str)
                    widget.setCurrentIndex(widget.count() - 1)
            elif isinstance(widget, QDateEdit):
                if isinstance(value, str):
                    if ' ' in value:
                        date_part = value.split()[0]
                        date_obj = datetime.strptime(date_part, '%Y-%m-%d').date()
                    else:
                        date_obj = datetime.strptime(value, '%Y-%m-%d').date()
                    widget.setDate(QDate(date_obj.year, date_obj.month, date_obj.day))
                elif isinstance(value, date):
                    widget.setDate(QDate(value.year, value.month, value.day))
                elif isinstance(value, datetime):
                    widget.setDate(QDate(value.year, value.month, value.day))
            elif isinstance(widget, QTimeEdit):
                if isinstance(value, str):
                    if ' ' in value:
                        time_part = value.split()[1]
                        time_obj = datetime.strptime(time_part, '%H:%M:%S').time()
                    else:
                        time_obj = datetime.strptime(value, '%H:%M:%S').time()
                    widget.setTime(QTime(time_obj.hour, time_obj.minute, time_obj.second))
                elif isinstance(value, datetime):
                    widget.setTime(QTime(value.hour, value.minute, value.second))
            else:
                if hasattr(widget, 'setText'):
                    widget.setText(str(value))
        except (ValueError, TypeError):
            if hasattr(widget, 'setText'):
                widget.setText(str(value))

    def _get_simple_widget_value(self, widget, col_type):
        if isinstance(widget, QSpinBox):
            return widget.value()
        if isinstance(widget, QDoubleSpinBox):
            return widget.value()
        if isinstance(widget, QCheckBox):
            return widget.isChecked()
        if isinstance(widget, QComboBox):
            return widget.currentText()
        if isinstance(widget, QDateEdit):
            if 'timestamp' in col_type.lower():
                d = widget.date().toPython()
                return d.strftime('%Y-%m-%d %H:%M:%S')
            return widget.date().toPython()
        if isinstance(widget, QTimeEdit):
            return widget.time().toString("HH:mm:ss")
        return widget.text().strip()

    def _build_composite_value(self, info: dict):
        type_name = info["type_name"]
        attrs = info["attrs"]
        widgets = info["widgets"]
        
        # Проверяем, выбрано ли значение из выпадающего списка
        value_combo = info.get("value_combo")
        if value_combo:
            selected_data = value_combo.itemData(value_combo.currentIndex())
            if selected_data and selected_data != "__new__":
                # Возвращаем выбранное значение как есть (оно уже в правильном формате)
                return selected_data
            # Если выбрано "Создать новое значение" или "-- Выберите значение --", продолжаем построение

        if not attrs and "__raw__" in widgets:
            raw = widgets["__raw__"].text().strip()
            return raw if raw else None

        values_sql = []
        for attr_name, attr_type in attrs:
            w = widgets.get(attr_name)
            if not w:
                values_sql.append("NULL")
                continue
            val = self._get_simple_widget_value(w, attr_type.lower())
            if val is None or val == "":
                values_sql.append("NULL")
            else:
                if isinstance(val, bool):
                    values_sql.append("TRUE" if val else "FALSE")
                elif isinstance(val, (int, float)):
                    values_sql.append(str(val))
                else:
                    s = str(val).replace("'", "''")
                    values_sql.append(f"'{s}'")
        inner = ", ".join(values_sql)
        return f"ROW({inner})::{type_name}"

    def validate_and_accept(self):
        first_col = self.columns_info[0]['name']
        first_type = self.columns_info[0].get('type', '').lower()
        fw_key = self.field_widgets[first_col]

        if isinstance(fw_key, dict) and "type_name" in fw_key:
            where_value = self._build_composite_value(fw_key)
        else:
            where_value = self._get_simple_widget_value(fw_key, first_type)

        data = {}
        errors = []

        for col in self.columns_info:
            col_name = col['name']
            if col_name == first_col:
                continue

            col_type = col.get('type', '')
            col_type_lower = col_type.lower()
            is_nullable = col.get('nullable', True)
            fw = self.field_widgets.get(col_name)
            if fw is None:
                continue

            if isinstance(fw, dict) and "type_name" in fw:
                val = self._build_composite_value(fw)
                if (val is None or val == "") and not is_nullable:
                    errors.append(f"Поле '{col_name}' обязательно для заполнения")
                if val not in (None, ""):
                    data[col_name] = val
            else:
                value = self._get_simple_widget_value(fw, col_type_lower)
                if (value in (None, "",) or (isinstance(fw, (QSpinBox, QDoubleSpinBox)) and value == 0)) and not is_nullable:
                    if isinstance(fw, (QSpinBox, QDoubleSpinBox)) and value == 0:
                        pass
                    else:
                        errors.append(f"Поле '{col_name}' обязательно для заполнения")
                if value not in (None, ""):
                    data[col_name] = value

        if errors:
            QMessageBox.warning(self, "Ошибка валидации", "\n".join(errors))
            return

        if not data:
            QMessageBox.warning(self, "Ошибка", "Нет данных для обновления")
            return

        where_clause = f"{first_col} = %s"
        success, error = self.controller.update_row(
            self.table_name, data, where_clause, [where_value]
        )
        if success:
            QMessageBox.information(self, "Успех", "Запись успешно обновлена")
            self.accept()
        else:
            QMessageBox.critical(self, "Ошибка", f"Не удалось обновить запись:\n{error}")