from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QDialogButtonBox, QMessageBox
)
import copy
from .select_table_dialog import SelectTableDialog
from .join_wizard_dialog import JoinWizardDialog
from .string_functions_dialog import StringFunctionsDialog

class DisplayOptionsDialog(QDialog):
    """Диалог опций вывода данных."""
    def __init__(self, controller, current_table=None, parent=None, task_dialog=None):
        super().__init__(parent)
        self.controller = controller
        self.current_table = current_table
        self.task_dialog = task_dialog

        self.selected_table = current_table
        self.selected_columns = None
        self.is_join_mode = False
        self.join_config = None
        self.join_tables = []
        self.join_conditions = []

        if self.task_dialog and getattr(self.task_dialog, 'is_join_mode', False) and hasattr(self.task_dialog, 'join_config'):
            self.join_config = copy.deepcopy(self.task_dialog.join_config)
            self.is_join_mode = True
            if self.join_config and 'join_conditions' in self.join_config:
                self.join_conditions = list(self.join_config['join_conditions'])
                self.join_tables = [j['table'] for j in self.join_conditions]

        self.setWindowTitle("Вывод данных")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        self.setup_ui()
        self.center_on_screen()

    def center_on_screen(self):
        screen = self.screen().geometry()
        self.move(screen.center() - self.rect().center())

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h3>Вывод данных</h3>"))

        select_table_btn = QPushButton("Выбрать таблицу")
        select_table_btn.setMinimumHeight(50)
        select_table_btn.clicked.connect(self.select_table)
        layout.addWidget(select_table_btn)

        add_join_btn = QPushButton("Добавить соединения (JOIN)")
        add_join_btn.setMinimumHeight(50)
        add_join_btn.clicked.connect(self.add_join)
        layout.addWidget(add_join_btn)

        string_func_btn = QPushButton("Строковые функции")
        string_func_btn.setMinimumHeight(50)
        string_func_btn.clicked.connect(self.apply_string_functions)
        layout.addWidget(string_func_btn)

        layout.addStretch()
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_dialog)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def select_table(self):
        dialog = SelectTableDialog(self.controller, self.selected_table, self, self.task_dialog)
        if dialog.exec_():
            self.selected_table = dialog.selected_table
            self.selected_columns = dialog.selected_columns
            self.is_join_mode = False
            self.join_tables = []
            self.join_conditions = []
            self.join_config = None
            self.accept()

    def add_join(self):
        if not self.selected_table:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите основную таблицу")
            return

        dialog = JoinWizardDialog(self.controller, self.selected_table, self)
        if dialog.exec_():
            new_cfg = dialog.get_join_config()
            if self.join_config:
                new_join = new_cfg['join_conditions'][0]
                self.join_config['join_conditions'].append(new_join)

                new_table = new_join['table']
                to_add_columns = [c for c in new_cfg['selected_columns'] if c.startswith(f"{new_table}.")]
                to_add_labels = []
                to_add_mapping = {}
                for disp, orig in new_cfg['column_mapping'].items():
                    if orig.startswith(f"{new_table}."):
                        to_add_labels.append(disp)
                        to_add_mapping[disp] = orig

                self.join_config['selected_columns'].extend(to_add_columns)
                self.join_config['column_labels'].extend(to_add_labels)
                if 'column_mapping' not in self.join_config:
                    self.join_config['column_mapping'] = {}
                self.join_config['column_mapping'].update(to_add_mapping)

                self.join_tables.append(new_table)
                self.join_conditions.append(new_join)
            else:
                self.join_config = new_cfg
                self.join_tables = [new_cfg['join_conditions'][0]['table']]
                self.join_conditions = [new_cfg['join_conditions'][0]]

            self.is_join_mode = True
            self.accept()

    def apply_string_functions(self):
        if self.task_dialog and self.task_dialog.is_join_mode:
            QMessageBox.information(self, "Недоступно", "Строковые функции недоступны при активных соединениях (JOIN).")
            return
        if not self.selected_table:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите таблицу")
            return

        columns_info = self.controller.get_table_columns(self.selected_table)
        dialog = StringFunctionsDialog(self.controller, self.selected_table, columns_info, self)
        dialog.exec_()

    def accept_dialog(self):
        if not self.selected_table:
            QMessageBox.warning(self, "Ошибка", "Выберите таблицу для вывода")
            return
        self.accept()