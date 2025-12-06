from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QHBoxLayout, QComboBox, QPushButton,
    QScrollArea, QWidget, QVBoxLayout, QDialogButtonBox, QCheckBox, QMessageBox, QInputDialog
)
from PySide6.QtCore import Qt

class SelectTableDialog(QDialog):
    """Диалог выбора таблицы с отображением и выбором столбцов."""
    def __init__(self, controller, current_table=None, parent=None, task_dialog=None):
        super().__init__(parent)
        self.controller = controller
        self.selected_table = current_table
        self.selected_columns = None
        self.scroll_area = None
        self.task_dialog = task_dialog

        self.columns_checks = {}
        self.scroll_widget = None
        self.scroll_layout = None

        self.setWindowTitle("Выбрать таблицу")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        self.setup_ui()
        self.center_on_screen()

    def center_on_screen(self):
        screen = self.screen().geometry()
        self.move(screen.center() - self.rect().center())

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h3>Выберите таблицу</h3>"))

        table_layout = QHBoxLayout()
        table_layout.addWidget(QLabel("Таблица:"))

        self.table_combo = QComboBox()
        self.table_combo.setMinimumWidth(200)
        self.table_combo.view().setMinimumWidth(240)
        tables = self.controller.get_all_tables()
        self.table_combo.addItems(tables)

        if 'task1' in tables:
            self.table_combo.setCurrentText('task1')
        elif self.selected_table and self.selected_table in tables:
            self.table_combo.setCurrentText(self.selected_table)

        table_layout.addWidget(self.table_combo)

        rename_btn = QPushButton("Переименовать")
        rename_btn.setMaximumWidth(140)
        rename_btn.clicked.connect(self.rename_table)
        table_layout.addWidget(rename_btn)

        layout.addLayout(table_layout)

        layout.addWidget(QLabel("<b>Выберите столбцы:</b>"))

        self.checkbox_style = """
        QCheckBox {
            color: white;
        }
        QCheckBox::indicator {
            width: 14px;
            height: 14px;
            border: 1px solid #c0c0c0;
            border-radius: 3px;
            background: white;
        }
        QCheckBox::indicator:hover {
            border: 1px solid #3a76d8;
            background: #f0f6ff;
        }
        QCheckBox::indicator:checked {
            background-color: #4a86e8;
            border: 1px solid #2a66c8;
            image: none;
        }
        QCheckBox::indicator:checked:hover {
            background-color: #3a76d8;
        }
        """

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_area.setWidget(self.scroll_widget)
        layout.addWidget(self.scroll_area)

        self.table_combo.currentTextChanged.connect(self._populate_column_checkboxes)
        self._populate_column_checkboxes(self.table_combo.currentText())

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_dialog)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _clear_layout_safe(self, vlayout):
        if vlayout is None:
            return
        while vlayout.count():
            item = vlayout.takeAt(vlayout.count() - 1)
            if not item:
                continue
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
            child = item.layout()
            if child is not None:
                self._clear_layout_safe(child)

    def _populate_column_checkboxes(self, table_name):
        if not hasattr(self, "scroll_layout") or self.scroll_layout is None:
            return

        self._clear_layout_safe(self.scroll_layout)
        self.columns_checks = {}

        if not table_name:
            return

        columns = self.controller.get_table_columns(table_name) or []
        for col in columns:
            cb = QCheckBox(f"{col['name']} ({col['type']})", parent=self.scroll_widget)
            cb.setChecked(True)
            cb.setLayoutDirection(Qt.LeftToRight)
            cb.setStyleSheet(self.checkbox_style)
            self.columns_checks[col['name']] = cb
            self.scroll_layout.addWidget(cb)

        self.scroll_layout.addStretch()

    def rename_table(self):
        old_name = self.table_combo.currentText()
        if not old_name:
            QMessageBox.warning(self, "Ошибка", "Выберите таблицу")
            return

        new_name, ok = QInputDialog.getText(
            self,
            "Переименование таблицы",
            f"Новое имя для таблицы '{old_name}':",
            text=old_name
        )

        if ok and new_name and new_name != old_name:
            success, error = self.controller.rename_table(old_name, new_name)
            if success:
                QMessageBox.information(self, "Успех", f"Таблица переименована: {old_name} → {new_name}")
                current_index = self.table_combo.currentIndex()
                self.table_combo.setItemText(current_index, new_name)

                if self.task_dialog:
                    # уведомим TaskDialog, чтобы он обновил имена task1/task2/task3 если нужно
                    try:
                        self.task_dialog.update_table_name(old_name, new_name)
                    except Exception:
                        pass

                self._populate_column_checkboxes(new_name)
            else:
                QMessageBox.critical(self, "Ошибка", f"Не удалось переименовать таблицу:\n{error}")

    def accept_dialog(self):
        self.selected_table = self.table_combo.currentText()
        selected = [name for name, check in self.columns_checks.items() if check.isChecked()]
        self.selected_columns = selected if selected else None
        self.accept()