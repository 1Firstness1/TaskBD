"""
Модуль диалога для расширенной работы с таблицами БД.
Содержит класс TaskDialog с возможностями управления данными и структурой таблиц.
"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                              QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
                              QComboBox, QLineEdit, QMenu, QInputDialog, QCheckBox,
                              QSpinBox, QFormLayout, QTextEdit, QDialogButtonBox, QWidget,
                              QScrollArea, QRadioButton, QButtonGroup, QGroupBox,
                              QDateEdit, QDoubleSpinBox, QTimeEdit, QListWidget, QTabWidget)
from PySide6.QtCore import Qt, QDate, QTime
from PySide6.QtGui import QAction
from controller import NumericTableItem, DateTableItem, BooleanTableItem, TimestampTableItem, ValidatedLineEdit
from logger import Logger
import psycopg2
from datetime import datetime, date
import copy


class TaskDialog(QDialog):
    """
    Диалог для расширенной работы с таблицами БД.
    """
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.logger = Logger()

        self.current_table = None
        self.current_columns = []
        self.all_columns_info = []
        self.all_enum_types = []        # список доступных ENUM типов
        self.all_composite_types = []   # список составных типов
        self.all_user_types = []        # объединенный список пользовательских типов

        self.current_sort_order = {}
        self.join_tables = []
        self.join_conditions = []
        self.current_where = None
        self.current_order_by = None
        self.current_group_by = None
        self.current_having = None
        self.is_join_mode = False
        self.original_column_names = {}

        # Накопители выражений (стакуемые функции)
        self.where_clauses = []        # список условий WHERE, объединяются через AND
        self.order_by_clauses = []     # список выражений ORDER BY
        self.group_by_clauses = []     # список столбцов для GROUP BY
        self.having_clauses = []       # список условий HAVING
        self.select_expressions = []   # дополнительные выражения в SELECT (агрегаты/CASE)

        # Имена таблиц
        self.task1_table_name = "task1"
        self.task2_table_name = "task2"
        self.task3_table_name = "task3"

        self.setWindowTitle("Техническое задание - Управление БД")
        self.setMinimumSize(1200, 700)

        self.refresh_user_types()
        self.setup_ui()

    def refresh_user_types(self):
        """
        Обновляет список пользовательских типов (ENUM и составные),
        чтобы можно было использовать их при создании столбцов.
        """
        try:
            self.all_enum_types = self.controller.list_enum_types()
        except Exception as e:
            self.logger.error(f"Ошибка получения ENUM типов: {e}")
            self.all_enum_types = []

        try:
            self.all_composite_types = self.controller.list_composite_types()
        except Exception as e:
            self.logger.error(f"Ошибка получения составных типов: {e}")
            self.all_composite_types = []

        self.all_user_types = list(self.all_enum_types) + list(self.all_composite_types)
        self.logger.info(f"Обновлены пользовательские типы: ENUM={self.all_enum_types}, COMPOSITE={self.all_composite_types}")

    def update_table_name(self, old_name, new_name):
        """Обновление имени таблицы в переменных."""
        if old_name == self.task1_table_name:
            self.task1_table_name = new_name
            self.logger.info(f"Обновлено имя таблицы task1: {old_name} -> {new_name}")
        elif old_name == self.task2_table_name:
            self.task2_table_name = new_name
            self.logger.info(f"Обновлено имя таблицы task2: {old_name} -> {new_name}")
        elif old_name == self.task3_table_name:
            self.task3_table_name = new_name
            self.logger.info(f"Обновлено имя таблицы task3: {old_name} -> {new_name}")

    def setup_ui(self):
        """Настройка пользовательского интерфейса."""
        layout = QVBoxLayout(self)

        # Заголовок
        title_layout = QHBoxLayout()
        title_label = QLabel("<h2>Управление структурой и данными БД</h2>")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        layout.addLayout(title_layout)

        # Статус таблицы (над таблицей)
        self.status_label = QLabel("<b>Статус:</b> Таблица не выбрана")
        self.status_label.setStyleSheet("background-color: #e3f2fd; padding: 10px; border-radius: 4px;")
        layout.addWidget(self.status_label)

        # Таблица данных
        self.data_table = QTableWidget()
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.data_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.data_table.setSelectionBehavior(QTableWidget.SelectItems)
        self.data_table.setSelectionMode(QTableWidget.SingleSelection)
        self.data_table.verticalHeader().setVisible(False)

        self.data_table.horizontalHeader().sectionClicked.connect(self.on_column_header_clicked)
        self.data_table.cellDoubleClicked.connect(self.on_cell_double_clicked)

        layout.addWidget(self.data_table)

        # Панель кнопок
        buttons_layout = QHBoxLayout()

        self.search_btn = QPushButton("Поиск")
        self.search_btn.clicked.connect(self.show_search_dialog)
        buttons_layout.addWidget(self.search_btn)

        self.reset_filters_btn = QPushButton("Сбросить фильтры")
        self.reset_filters_btn.clicked.connect(self.reset_all_filters)
        buttons_layout.addWidget(self.reset_filters_btn)

        self.edit_btn = QPushButton("Редактировать")
        self.edit_btn.clicked.connect(self.show_edit_menu)
        buttons_layout.addWidget(self.edit_btn)

        self.add_btn = QPushButton("Добавить")
        self.add_btn.clicked.connect(self.show_add_menu)
        buttons_layout.addWidget(self.add_btn)

        self.delete_btn = QPushButton("Удалить")
        self.delete_btn.clicked.connect(self.show_delete_menu)
        buttons_layout.addWidget(self.delete_btn)

        # Типы данных
        self.types_btn = QPushButton("Типы данных")
        self.types_btn.clicked.connect(self.open_types_dialog)
        buttons_layout.addWidget(self.types_btn)

        buttons_layout.addStretch()

        self.refresh_tables_btn = QPushButton("Обновить таблицы")
        self.refresh_tables_btn.clicked.connect(self.refresh_tables)
        buttons_layout.addWidget(self.refresh_tables_btn)

        self.display_btn = QPushButton("Вывод")
        self.display_btn.clicked.connect(self.show_display_options)
        buttons_layout.addWidget(self.display_btn)

        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(close_btn)

        layout.addLayout(buttons_layout)

    def update_status(self):
        """Обновление статуса таблицы."""
        if self.current_table:
            join_info = f", {len(self.join_tables)} соединений" if self.join_tables else ""
            self.status_label.setText(f"<b>Статус:</b> Таблица: {self.current_table}{join_info}")
        else:
            self.status_label.setText("<b>Статус:</b> Таблица не выбрана")

    def reset_all_filters(self):
        """Сброс всех фильтров, группировок, сортировок и перезагрузка таблицы."""
        if not self.current_table:
            QMessageBox.warning(self, "Ошибка", "Таблица не выбрана")
            return

        self.current_sort_order = {}
        self.current_where = None
        self.current_order_by = None
        self.current_group_by = None
        self.current_having = None
        self.join_tables = []
        self.join_conditions = []
        self.is_join_mode = False
        self.original_column_names = {}

        self.where_clauses = []
        self.order_by_clauses = []
        self.group_by_clauses = []
        self.having_clauses = []
        self.select_expressions = []

        self.load_table_data_filtered()
        self.update_status()
        QMessageBox.information(self, "Успех", "Все фильтры и соединения сброшены")
        self.logger.info(f"Фильтры сброшены для таблицы {self.current_table}")

    def refresh_tables(self):
        """Обновление таблиц task1, task2 и task3 с тестовыми данными."""
        try:
            existing_tables = self.controller.get_all_tables()

            if self.task1_table_name in existing_tables:
                self.controller.drop_table(self.task1_table_name)
                self.logger.info(f"Удалена существующая таблица {self.task1_table_name}")
            if self.task2_table_name in existing_tables:
                self.controller.drop_table(self.task2_table_name)
                self.logger.info(f"Удалена существующая таблица {self.task2_table_name}")
            if self.task3_table_name in existing_tables:
                self.controller.drop_table(self.task3_table_name)
                self.logger.info(f"Удалена существующая таблица {self.task3_table_name}")

            self.create_task1_table()
            self.create_task2_table()
            self.create_task3_table()

            QMessageBox.information(
                self, "Успех",
                f"Таблицы {self.task1_table_name}, {self.task2_table_name} и {self.task3_table_name} успешно обновлены"
            )
            self.logger.info(
                f"Таблицы {self.task1_table_name}, {self.task2_table_name} и {self.task3_table_name} успешно обновлены"
            )
        except Exception as e:
            self.logger.error(f"Ошибка обновления таблиц: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось обновить таблицы:\n{str(e)}")

    def create_task1_table(self):
        """Создание таблицы task1 с тестовыми данными."""
        self.controller.create_table(self.task1_table_name, [
            {'name': 'id', 'type': 'SERIAL PRIMARY KEY'},
            {'name': 'name', 'type': 'VARCHAR(100) NOT NULL'},
            {'name': 'description', 'type': 'TEXT'},
            {'name': 'price', 'type': 'NUMERIC(10,2)'},
            {'name': 'quantity', 'type': 'INTEGER'},
            {'name': 'is_active', 'type': 'BOOLEAN DEFAULT true'},
            {'name': 'created_date', 'type': 'DATE DEFAULT CURRENT_DATE'},
            {'name': 'updated_at', 'type': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'}
        ])

        test_data = [
            ('Товар 1', 'Описание товара 1', 1500.50, 10, True, '2024-01-15', '2024-01-15 10:30:00'),
            ('Товар 2', 'Описание товара 2', 2300.75, 5, True, '2024-01-16', '2024-01-16 14:20:00'),
            ('Товар 3', 'Описание товара 3', 800.25, 20, False, '2024-01-17', '2024-01-17 09:15:00'),
            ('Товар 4', 'Описание товара 4', 3500.00, 3, True, '2024-01-18', '2024-01-18 16:45:00'),
            ('Товар 5', 'Описание товара 5', 1200.80, 15, True, '2024-01-19', '2024-01-19 11:30:00')
        ]

        for d in test_data:
            self.controller.insert_row(self.task1_table_name, {
                'name': d[0],
                'description': d[1],
                'price': d[2],
                'quantity': d[3],
                'is_active': d[4],
                'created_date': d[5],
                'updated_at': d[6]
            })

    def create_task2_table(self):
        """Создание таблицы task2 с тестовыми данными."""
        self.controller.create_table(self.task2_table_name, [
            {'name': 'id', 'type': 'SERIAL PRIMARY KEY'},
            {'name': 'title', 'type': 'VARCHAR(200) NOT NULL'},
            {'name': 'content', 'type': 'TEXT'},
            {'name': 'priority', 'type': 'INTEGER CHECK (priority BETWEEN 1 AND 5)'},
            {'name': 'status', 'type': "VARCHAR(50) DEFAULT 'pending'"},
            {'name': 'due_date', 'type': 'DATE'},
            {'name': 'completed', 'type': 'BOOLEAN DEFAULT false'},
            {'name': 'tags', 'type': 'TEXT[]'},
            {'name': 'metadata', 'type': 'JSONB'}
        ])

        test_data = [
            ('Задача 1', 'Содержимое задачи 1', 3, 'in_progress', '2024-02-15', False,
             ['важно', 'срочно'], '{"author": "Иван", "department": "IT"}'),
            ('Задача 2', 'Содержимое задачи 2', 1, 'completed', '2024-02-10', True,
             ['тестирование'], '{"author": "Петр", "department": "QA"}'),
            ('Задача 3', 'Содержимое задачи 3', 5, 'pending', '2024-02-20', False,
             ['разработка'], '{"author": "Мария", "department": "Dev"}'),
            ('Задача 4', 'Содержимое задачи 4', 2, 'in_progress', '2024-02-12', False,
             ['документация'], '{"author": "Анна", "department": "Docs"}'),
            ('Задача 5', 'Содержимое задачи 5', 4, 'pending', '2024-02-25', False,
             ['анализ'], '{"author": "Сергей", "department": "Analytics"}')
        ]

        for d in test_data:
            self.controller.insert_row(self.task2_table_name, {
                'title': d[0],
                'content': d[1],
                'priority': d[2],
                'status': d[3],
                'due_date': d[4],
                'completed': d[5],
                'tags': d[6],
                'metadata': d[7]
            })

    def create_task3_table(self):
        """Создание таблицы task3 с тестовыми данными."""
        self.controller.create_table(self.task3_table_name, [
            {'name': 'id', 'type': 'SERIAL PRIMARY KEY'},
            {'name': 'code', 'type': 'VARCHAR(50) NOT NULL'},
            {'name': 'category', 'type': 'VARCHAR(100)'},
            {'name': 'amount', 'type': 'NUMERIC(12,2)'},
            {'name': 'active', 'type': 'BOOLEAN DEFAULT true'},
            {'name': 'event_date', 'type': 'DATE'},
            {'name': 'event_ts', 'type': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'}
        ])

        test_data = [
            ('A-100', 'Продажи', 10000.50, True, '2024-03-01', '2024-03-01 09:00:00'),
            ('B-200', 'Закупки', 5500.00, False, '2024-03-05', '2024-03-05 13:30:00'),
            ('C-300', 'Склад', 750.75, True, '2024-03-10', '2024-03-10 15:45:00'),
            ('D-400', 'Финансы', 123000.00, True, '2024-03-15', '2024-03-15 10:10:00'),
            ('E-500', 'Отчеты', 900.90, False, '2024-03-20', '2024-03-20 18:20:00')
        ]
        for d in test_data:
            self.controller.insert_row(self.task3_table_name, {
                'code': d[0],
                'category': d[1],
                'amount': d[2],
                'active': d[3],
                'event_date': d[4],
                'event_ts': d[5]
            })

    def on_cell_double_clicked(self, row, column):
        """Открытие окна действий над столбцом."""
        if not self.current_table or column >= len(self.current_columns):
            return

        column_name = self.current_columns[column]
        cell_value = self.data_table.item(row, column).text() if self.data_table.item(row, column) else ""

        orig_column_name = column_name
        if self.is_join_mode and column_name in self.original_column_names:
            orig_column_name = self.original_column_names[column_name]

        dialog = ColumnActionsDialog(
            controller=self.controller,
            table_name=self.current_table,
            columns_info=self.all_columns_info,
            selected_column=orig_column_name,
            prefill_value=cell_value,
            parent=self
        )
        dialog.exec_()

    def on_column_header_clicked(self, logical_index):
        QMessageBox.information(
            self, "Сортировка",
            "Сортировка доступна через окно действий: дважды кликните по ячейке и выберите 'Сортировка'."
        )

    def show_search_dialog(self):
        """Показ диалога поиска."""
        if self.is_join_mode:
            QMessageBox.information(self, "Недоступно", "Поиск недоступен при активных соединениях (JOIN).")
            return
        if not self.current_table:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите таблицу через 'Вывод'")
            return

        dialog = SearchDialog(self.controller, self.current_table, self.all_columns_info, self)
        if dialog.exec_():
            self.current_where = dialog.search_condition
            self.load_table_data_filtered(
                where=dialog.search_condition,
                params=getattr(dialog, 'search_params', None)
            )

    def show_edit_menu(self):
        if self.is_join_mode:
            QMessageBox.information(self, "Недоступно", "Редактирование недоступно при активных JOIN.")
            return
        if not self.current_table:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите таблицу через 'Вывод'")
            return

        dialog = EditMenuDialog(self.controller, self.current_table, self.all_columns_info,
                                self.data_table, self)
        if dialog.exec_():
            self.current_columns = []
            self.all_columns_info = self.controller.get_table_columns(self.current_table)
            self.load_table_data_filtered(
                where=self.current_where,
                order_by=self.current_order_by,
                group_by=self.current_group_by,
                having=self.current_having
            )

    def show_add_menu(self):
        if self.is_join_mode:
            QMessageBox.information(self, "Недоступно", "Создание/добавление недоступно при активных JOIN.")
            return
        if not self.current_table:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите таблицу через 'Вывод'")
            return

        dialog = AddMenuDialog(self.controller, self.current_table, self.all_columns_info, self)
        if dialog.exec_():
            self.current_columns = []
            self.all_columns_info = self.controller.get_table_columns(self.current_table)
            self.load_table_data_filtered(
                where=self.current_where,
                order_by=self.current_order_by,
                group_by=self.current_group_by,
                having=self.current_having
            )

    def show_delete_menu(self):
        if self.is_join_mode:
            QMessageBox.information(self, "Недоступно", "Удаление недоступно при активных JOIN.")
            return
        if not self.current_table:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите таблицу через 'Вывод'")
            return

        selected_column = None
        selected_items = self.data_table.selectedItems()
        if selected_items:
            selected_col_idx = self.data_table.column(selected_items[0])
            if 0 <= selected_col_idx < len(self.current_columns):
                selected_column = self.current_columns[selected_col_idx]

        dialog = DeleteMenuDialog(self.controller, self.current_table, self.all_columns_info,
                                  self.data_table, selected_column, self)
        if dialog.exec_():
            self.current_columns = []
            self.all_columns_info = self.controller.get_table_columns(self.current_table)
            self.load_table_data_filtered(
                where=self.current_where,
                order_by=self.current_order_by,
                group_by=self.current_group_by,
                having=self.current_having
            )

    def refresh_with_current_clauses(self):
        """Пересобирает и применяет стек условий."""
        where = " AND ".join(self.where_clauses) if self.where_clauses else None
        order_by = ", ".join(self.order_by_clauses) if self.order_by_clauses else None
        group_by = ", ".join(self.group_by_clauses) if self.group_by_clauses else None
        having = " AND ".join(self.having_clauses) if self.having_clauses else None

        select_cols = None
        display_headers = None

        if self.group_by_clauses or self.select_expressions:
            select_cols = []
            display_headers = []

            def label_for_column(full_col: str) -> str:
                if hasattr(self, 'original_column_names') and self.original_column_names:
                    for disp, orig in self.original_column_names.items():
                        if orig == full_col:
                            return disp
                return full_col.replace('.', '_')

            for gb in self.group_by_clauses:
                select_cols.append(gb)
                display_headers.append(label_for_column(gb) if self.is_join_mode else gb)

            for expr in self.select_expressions:
                select_cols.append(expr)
                up = expr.upper()
                alias = None
                if " AS " in up:
                    parts = expr.rsplit(" AS ", 1)
                    alias = parts[-1].strip().strip('"')
                display_headers.append(alias if alias else expr)

        self.current_where = where
        self.current_order_by = order_by
        self.current_group_by = group_by
        self.current_having = having

        if self.is_join_mode:
            self.load_table_data_filtered(
                columns=display_headers if display_headers else None,
                where=where or self.join_config.get('where'),
                order_by=order_by or self.join_config.get('order_by'),
                group_by=group_by,
                having=having,
                params=None,
                _select_override=(select_cols if select_cols else None)
            )
        else:
            self.load_table_data_filtered(
                columns=display_headers if display_headers else None,
                where=where,
                order_by=order_by,
                group_by=group_by,
                having=having,
                params=None,
                _select_override=(select_cols if select_cols else None)
            )

    def add_sort_clause(self, column, direction):
        clause = f"{column} {direction}"
        self.order_by_clauses = [c for c in self.order_by_clauses if not c.startswith(f"{column} ")]
        self.order_by_clauses.append(clause)
        self.logger.info(f"Добавлена сортировка: {clause}")
        self.refresh_with_current_clauses()

    def add_where_clause(self, clause, params=None):
        """
        Добавляет условие в стек WHERE. Если переданы params, они не хранятся
        (для сложных фильтров мы собираем строку полностью), но оставляем
        параметр для совместимости.
        """
        if clause:
            self.where_clauses.append(clause)
            self.logger.info(f"Добавлен фильтр: {clause}")
            self.refresh_with_current_clauses()

    def add_group_by_column(self, column):
        if column not in self.group_by_clauses:
            self.group_by_clauses.append(column)
            self.logger.info(f"Добавлена группировка по: {column}")
            self.refresh_with_current_clauses()

    def add_select_aggregate(self, expression):
        if expression and expression not in self.select_expressions:
            self.select_expressions.append(expression)
            self.logger.info(f"Добавлен агрегат в SELECT: {expression}")
            self.refresh_with_current_clauses()

    def add_having_clause(self, clause):
        if clause:
            self.having_clauses.append(clause)
            self.logger.info(f"Добавлен HAVING: {clause}")
            self.refresh_with_current_clauses()

    def add_select_expression(self, expression: str):
        """Добавляет вычисляемое выражение в список select_expressions."""
        if expression and expression not in self.select_expressions:
            self.select_expressions.append(expression)

    def load_table_data_filtered(self, columns=None, where=None, order_by=None, group_by=None, having=None,
                                 params=None, _select_override=None):
        """Загрузка данных таблицы с учетом условий / группировок / вычисляемых столбцов."""
        if not self.current_table:
            return

        try:
            # JOIN режим
            if self.is_join_mode:
                if _select_override is not None:
                    base_select_list = list(_select_override)
                else:
                    if columns:
                        base_select_list = []
                        for disp in columns:
                            if disp in self.original_column_names:
                                base_select_list.append(self.original_column_names[disp])
                            else:
                                base_select_list.append(disp)
                    else:
                        base_select_list = list(self.join_config['selected_columns'])

                for expr in self.select_expressions:
                    if expr not in base_select_list:
                        base_select_list.append(expr)

                display_headers = []
                reverse_map = {orig: disp for disp, orig in self.original_column_names.items()}

                for sel in base_select_list:
                    up = sel.upper()
                    alias = None
                    if " AS " in up:
                        parts = sel.rsplit(" AS ", 1)
                        alias = parts[-1].strip().strip('"')
                    if alias:
                        display_headers.append(alias)
                    else:
                        if '.' in sel and '(' not in sel and ' ' not in sel:
                            display_headers.append(reverse_map.get(sel, sel.replace('.', '_')))
                        else:
                            display_headers.append(sel)

                self.current_columns = display_headers

                results = self.controller.execute_join(
                    self.join_config['tables_info'],
                    base_select_list,
                    self.join_config['join_conditions'],
                    where or self.join_config.get('where'),
                    order_by or self.join_config.get('order_by'),
                    group_by,
                    having
                )
                data = results

            # Обычный режим
            else:
                if _select_override is not None:
                    select_list = list(_select_override)
                    for expr in self.select_expressions:
                        if expr not in select_list:
                            select_list.append(expr)
                    display_headers = []
                    for sel in select_list:
                        up = sel.upper()
                        alias = None
                        if " AS " in up:
                            parts = sel.rsplit(" AS ", 1)
                            alias = parts[-1].strip().strip('"')
                        display_headers.append(alias if alias else sel)
                    self.current_columns = display_headers
                    data = self.controller.get_table_data(
                        self.current_table,
                        select_list,
                        where,
                        order_by,
                        group_by,
                        having,
                        params
                    )
                else:
                    if columns is None:
                        base_cols_list = [c['name'] for c in self.all_columns_info]
                        base_cols = '*'
                    else:
                        base_cols_list = list(columns)
                        base_cols = ', '.join(base_cols_list)

                    if base_cols == '*':
                        # '*' + выражения
                        select_list = ['*'] + list(self.select_expressions)
                        self.current_columns = [c['name'] for c in self.all_columns_info]
                        for expr in self.select_expressions:
                            up = expr.upper()
                            alias = None
                            if " AS " in up:
                                parts = expr.rsplit(" AS ", 1)
                                alias = parts[-1].strip().strip('"')
                            self.current_columns.append(alias if alias else expr)
                    else:
                        select_list = base_cols_list + list(self.select_expressions)
                        display_headers = list(base_cols_list)
                        for expr in self.select_expressions:
                            up = expr.upper()
                            alias = None
                            if " AS " in up:
                                parts = expr.rsplit(" AS ", 1)
                                alias = parts[-1].strip().strip('"')
                            display_headers.append(alias if alias else expr)
                        self.current_columns = display_headers

                    data = self.controller.get_table_data(
                        self.current_table,
                        select_list,
                        where,
                        order_by,
                        group_by,
                        having,
                        params
                    )

            # Отрисовка таблицы
            self.data_table.clearSpans()
            self.data_table.setRowCount(0)
            self.data_table.setColumnCount(len(self.current_columns))
            self.data_table.setHorizontalHeaderLabels(self.current_columns)
            self.data_table.setRowCount(len(data))

            from datetime import datetime as _dt, date as _date
            for row_idx, row_data in enumerate(data):
                for col_idx, value in enumerate(row_data):
                    str_value = str(value) if value is not None else ""
                    if isinstance(value, (int, float)):
                        item = NumericTableItem(str_value, value)
                    elif isinstance(value, _date):
                        item = DateTableItem(str_value, value)
                    elif isinstance(value, _dt):
                        item = TimestampTableItem(str_value, value)
                    elif isinstance(value, bool):
                        item = BooleanTableItem(str_value, value)
                    else:
                        item = QTableWidgetItem(str_value)
                    self.data_table.setItem(row_idx, col_idx, item)

            mode = "JOIN" if self.is_join_mode else "TABLE"
            self.logger.info(f"Загружены данные ({mode}): {len(data)} строк")

        except Exception as e:
            self.logger.error(f"Ошибка при загрузке данных: {str(e)}")
            QMessageBox.critical(self, "Ошибка загрузки", f"Не удалось загрузить данные: {str(e)}")

    def show_display_options(self):
        """Показ опций вывода данных с выбором таблицы."""
        dialog = DisplayOptionsDialog(self.controller, self.current_table, self, self)
        if dialog.exec_():
            self.current_table = dialog.selected_table
            self.join_tables = dialog.join_tables
            self.join_conditions = dialog.join_conditions
            self.is_join_mode = dialog.is_join_mode
            self.update_status()

            if not self.current_table:
                return

            self.all_columns_info = self.controller.get_table_columns(self.current_table)
            self.current_columns = []
            self.current_where = None
            self.current_order_by = None
            self.current_group_by = None
            self.current_having = None
            self.original_column_names = {}

            self.where_clauses = []
            self.order_by_clauses = []
            self.group_by_clauses = []
            self.having_clauses = []
            self.select_expressions = []

            if dialog.is_join_mode:
                self.join_config = dialog.join_config
                self.execute_join_display(dialog.join_config)
            else:
                self.current_columns = dialog.selected_columns if dialog.selected_columns else [c['name'] for c in self.all_columns_info]
                self.load_table_data_filtered(columns=self.current_columns)

    def execute_join_display(self, join_config):
        """Выполнение и отображение результатов JOIN."""
        try:
            results = self.controller.execute_join(
                join_config['tables_info'],
                join_config['selected_columns'],
                join_config['join_conditions'],
                join_config.get('where'),
                join_config.get('order_by'),
                None,
                None
            )

            if results:
                if 'column_mapping' in join_config:
                    self.original_column_names = join_config['column_mapping']
                else:
                    self.original_column_names = {}
                    for i, display_name in enumerate(join_config['column_labels']):
                        if i < len(join_config['selected_columns']):
                            self.original_column_names[display_name] = join_config['selected_columns'][i]

                self.current_columns = join_config['column_labels']
                self.data_table.clearSpans()
                self.data_table.setRowCount(0)
                self.data_table.setColumnCount(len(self.current_columns))
                self.data_table.setHorizontalHeaderLabels(self.current_columns)
                self.data_table.setRowCount(len(results))

                for row_idx, row_data in enumerate(results):
                    for col_idx, value in enumerate(row_data):
                        str_value = str(value) if value is not None else ""
                        if isinstance(value, (int, float)):
                            item = NumericTableItem(str_value, value)
                        elif isinstance(value, date):
                            item = DateTableItem(str_value, value)
                        elif isinstance(value, datetime):
                            item = TimestampTableItem(str_value, value)
                        elif isinstance(value, bool):
                            item = BooleanTableItem(str_value, value)
                        else:
                            item = QTableWidgetItem(str_value)
                        self.data_table.setItem(row_idx, col_idx, item)

                self.logger.info(f"Выполнен JOIN запрос: {len(results)} строк")
            else:
                QMessageBox.information(self, "Результат", "JOIN-запрос не вернул результатов")
        except psycopg2.Error as e:
            self.logger.error(f"Ошибка JOIN: {str(e)}")
            error_msg = str(e)
            if "column" in error_msg.lower():
                hint = "Проверьте, что все указанные столбцы существуют"
            elif "table" in error_msg.lower():
                hint = "Проверьте, что таблицы существуют"
            else:
                hint = "Проверьте условия соединения"
            QMessageBox.critical(
                self, "Ошибка выполнения JOIN",
                f"Не удалось выполнить соединение:\n\n{hint}\n\nТехническая информация:\n{error_msg}"
            )
        except Exception as e:
            self.logger.error(f"Неожиданная ошибка JOIN: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Неожиданная ошибка: {str(e)}")

    def execute_join_with_sort(self, join_config):
        self.join_config = join_config
        self.execute_join_display(join_config)

    def open_types_dialog(self):
        dialog = TypeManagementDialog(self.controller, self)
        dialog.exec_()
        # после изменений типов обновим кэш пользовательских типов
        self.refresh_user_types()


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
        """Центрирование диалога на экране."""
        screen = self.screen().geometry()
        self.move(screen.center() - self.rect().center())

    def setup_ui(self):
        """Настройка UI."""
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
        """Редактирование столбца."""
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
        """Редактирование записи."""
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
        """Принятие диалога."""
        self.accept()


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
        """Центрирование диалога на экране."""
        screen = self.screen().geometry()
        self.move(screen.center() - self.rect().center())

    def setup_ui(self):
        """Настройка UI."""
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
        """Добавление столбца."""
        # передаём в диалог список пользовательских типов через parent (TaskDialog)
        user_types = []
        if isinstance(self.parent(), TaskDialog):
            user_types = self.parent().all_user_types
        dialog = AddColumnDialog(self.controller, self.table_name, user_types, self)
        if dialog.exec_():
            self.action_taken = True
            self.accept()

    def add_record(self):
        """Добавление записи."""
        dialog = AddRecordDialog(self.controller, self.table_name, self.columns_info, self)
        if dialog.exec_():
            self.action_taken = True
            self.accept()

    def accept_dialog(self):
        """Принятие диалога."""
        self.accept()


class DeleteMenuDialog(QDialog):
    """Диалог меню удаления."""
    def __init__(self, controller, table_name, columns_info, data_table, selected_column=None, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.table_name = table_name
        self.columns_info = columns_info
        self.data_table = data_table
        self.selected_column = selected_column
        self.action_taken = False

        self.setWindowTitle("Удалить")
        self.setMinimumWidth(400)
        self.setMinimumHeight(250)
        self.setup_ui()
        self.center_on_screen()

    def center_on_screen(self):
        """Центрирование диалога на экране."""
        screen = self.screen().geometry()
        self.move(screen.center() - self.rect().center())

    def setup_ui(self):
        """Настройка UI."""
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("<h3>Выберите действие</h3>"))

        delete_column_btn = QPushButton("Удалить столбец")
        delete_column_btn.setMinimumHeight(50)
        delete_column_btn.clicked.connect(self.delete_column)
        layout.addWidget(delete_column_btn)

        delete_record_btn = QPushButton("Удалить запись")
        delete_record_btn.setMinimumHeight(50)
        delete_record_btn.clicked.connect(self.delete_record)
        layout.addWidget(delete_record_btn)

        layout.addStretch()

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_dialog)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def delete_column(self):
        """Удаление столбца, выбранного в текущей таблице, с подтверждением."""
        column_to_delete = self.selected_column
        if not column_to_delete:
            selected_items = self.data_table.selectedItems()
            if selected_items:
                selected_col_idx = self.data_table.column(selected_items[0])
                header_item = self.data_table.horizontalHeaderItem(selected_col_idx)
                if header_item:
                    column_to_delete = header_item.text()

        if not column_to_delete:
            QMessageBox.warning(self, "Ошибка", "Выберите ячейку столбца, который хотите удалить")
            return

        confirm = QMessageBox.question(
            self,
            "Подтверждение",
            f"Вы уверены, что хотите удалить столбец '{column_to_delete}'?\nЭто действие необратимо!",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm != QMessageBox.Yes:
            return

        success, error = self.controller.drop_column(self.table_name, column_to_delete)
        if success:
            QMessageBox.information(self, "Успех", f"Столбец '{column_to_delete}' удален")
            self.action_taken = True
            self.accept()
        else:
            QMessageBox.critical(self, "Ошибка", f"Не удалось удалить столбец:\n{error}")

    def delete_record(self):
        """Удаление записи."""
        if not self.data_table.rowCount():
            QMessageBox.warning(self, "Ошибка", "Таблица пуста, нечего удалять")
            return

        selected_items = self.data_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Ошибка", "Выберите ячейку в записи для удаления")
            return

        item = selected_items[0]
        row = item.row()

        if row < 0 or row >= self.data_table.rowCount():
            QMessageBox.warning(self, "Ошибка", "Неверная строка")
            return

        confirm = QMessageBox.question(
            self,
            "Подтверждение",
            "Вы уверены, что хотите удалить эту запись?",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm != QMessageBox.Yes:
            return

        if not self.data_table.columnCount():
            QMessageBox.warning(self, "Ошибка", "Нет данных для удаления")
            return

        first_col_item = self.data_table.horizontalHeaderItem(0)
        if not first_col_item:
            return
        first_col = first_col_item.text()
        first_value = self.data_table.item(row, 0).text()

        where_clause = f"{first_col} = %s"
        success, error = self.controller.delete_row(self.table_name, where_clause, [first_value])

        if success:
            QMessageBox.information(self, "Успех", "Запись успешно удалена")
            self.action_taken = True
            self.accept()
        else:
            QMessageBox.critical(self, "Ошибка", f"Не удалось удалить запись:\n{error}")

    def accept_dialog(self):
        """Принятие диалога."""
        self.accept()


class AddColumnDialog(QDialog):
    """Диалог добавления нового столбца."""
    def __init__(self, controller, table_name, user_types=None, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.table_name = table_name
        self.user_types = user_types or []

        self.setWindowTitle("Добавить столбец")
        self.setMinimumWidth(400)
        self.setup_ui()
        self.center_on_screen()

    def center_on_screen(self):
        """Центрирование диалога на экране."""
        screen = self.screen().geometry()
        self.move(screen.center() - self.rect().center())

    def setup_ui(self):
        """Настройка UI."""
        layout = QFormLayout(self)

        checkbox_style = """
                QCheckBox {
                    color: #333333;
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

        self.name_edit = QLineEdit()
        layout.addRow("Имя столбца:", self.name_edit)

        self.type_combo = QComboBox()
        self.type_combo.setMinimumWidth(220)
        self.type_combo.view().setMinimumWidth(260)

        # базовые типы
        base_types = [
            "INTEGER", "BIGINT", "VARCHAR(100)", "VARCHAR(200)",
            "TEXT", "BOOLEAN", "DATE", "TIMESTAMP", "NUMERIC"
        ]
        for t in base_types:
            self.type_combo.addItem(t)

        # пользовательские типы (ENUM и составные)
        if self.user_types:
            self.type_combo.insertSeparator(self.type_combo.count())
            for ut in self.user_types:
                # помечаем их как "user:" визуально, но в value - чистое имя
                self.type_combo.addItem(f"{ut} (user type)", ut)

        layout.addRow("Тип данных:", self.type_combo)

        self.nullable_check = QCheckBox("Может быть NULL")
        self.nullable_check.setChecked(True)
        self.nullable_check.setStyleSheet(checkbox_style)
        layout.addRow("", self.nullable_check)

        self.default_edit = QLineEdit()
        layout.addRow("Значение по умолчанию:", self.default_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_dialog)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _current_type_value(self):
        """Возвращает реальное значение типа (учитывая пользовательские типы)."""
        idx = self.type_combo.currentIndex()
        data = self.type_combo.itemData(idx)
        if data:
            return data
        # если data нет, берём текст до пробела (на случай помеченных user type)
        text = self.type_combo.currentText()
        if " (user type)" in text:
            return text.split(" (user type)", 1)[0]
        return text

    def accept_dialog(self):
        """Принятие диалога с валидацией."""
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите имя столбца")
            return

        data_type = self._current_type_value()
        nullable = self.nullable_check.isChecked()
        default = self.default_edit.text().strip() if self.default_edit.text().strip() else None

        success, error = self.controller.add_column(
            self.table_name, name, data_type, nullable, default
        )

        if success:
            QMessageBox.information(self, "Успех", f"Столбец '{name}' успешно добавлен")
            self.accept()
        else:
            QMessageBox.critical(self, "Ошибка", f"Не удалось добавить столбец:\n{error}")


class EditColumnDialog(QDialog):
    """Диалог редактирования столбца (работает со столбцом, где выбрана ячейка)."""
    def __init__(self, controller, table_name, columns_info, selected_column=None, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.table_name = table_name
        self.columns_info = columns_info
        self.selected_column = selected_column

        self.setWindowTitle("Редактировать столбец")
        self.setMinimumWidth(450)
        self.setup_ui()
        self.center_on_screen()

    def center_on_screen(self):
        """Центрирование диалога на экране."""
        screen = self.screen().geometry()
        self.move(screen.center() - self.rect().center())

    def setup_ui(self):
        """Настройка UI."""
        layout = QVBoxLayout(self)

        info_text = self.selected_column if self.selected_column else "не выбран"
        layout.addWidget(QLabel(f"Выбранный столбец: <b>{info_text}</b>"))

        operations_label = QLabel("<b>Выберите операцию:</b>")
        layout.addWidget(operations_label)

        rename_btn = QPushButton("Переименовать столбец")
        rename_btn.clicked.connect(self.rename_column)
        layout.addWidget(rename_btn)

        change_type_btn = QPushButton("Изменить тип данных")
        change_type_btn.clicked.connect(self.change_column_type)
        layout.addWidget(change_type_btn)

        set_constraint_btn = QPushButton("Установить ограничение")
        set_constraint_btn.clicked.connect(self.set_constraint)
        layout.addWidget(set_constraint_btn)

        drop_constraint_btn = QPushButton("Снять ограничение")
        drop_constraint_btn.clicked.connect(self.drop_constraint)
        layout.addWidget(drop_constraint_btn)

        layout.addStretch()

        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def get_current_column(self):
        """Возвращает столбец, который был выбран в таблице."""
        return self.selected_column

    def _ensure_column_selected(self):
        if not self.selected_column:
            QMessageBox.warning(self, "Ошибка", "Выберите ячейку столбца, который хотите редактировать")
            return False
        return True

    def rename_column(self):
        """Переименование столбца."""
        if not self._ensure_column_selected():
            return
        old_name = self.get_current_column()
        new_name, ok = QInputDialog.getText(
            self, "Переименование столбца",
            f"Новое имя для столбца '{old_name}':",
            text=old_name
        )

        if ok and new_name and new_name != old_name:
            success, error = self.controller.rename_column(self.table_name, old_name, new_name)
            if success:
                QMessageBox.information(self, "Успех", f"Столбец переименован: {old_name} → {new_name}")
                for col in self.columns_info:
                    if col['name'] == old_name:
                        col['name'] = new_name
                        break
                self.selected_column = new_name
            else:
                QMessageBox.critical(self, "Ошибка", f"Не удалось переименовать столбец:\n{error}")

    def change_column_type(self):
        """Изменение типа данных столбца."""
        if not self._ensure_column_selected():
            return
        column = self.get_current_column()

        # получаем возможные пользовательские типы из контроллера
        try:
            enum_types = self.controller.list_enum_types()
        except Exception:
            enum_types = []
        try:
            comp_types = self.controller.list_composite_types()
        except Exception:
            comp_types = []
        user_types = enum_types + comp_types

        types = [
            "INTEGER", "BIGINT", "VARCHAR(100)", "VARCHAR(200)",
            "TEXT", "BOOLEAN", "DATE", "TIMESTAMP", "NUMERIC"
        ]
        if user_types:
            types.append("---------- пользовательские ----------")
            types.extend(user_types)

        new_type, ok = QInputDialog.getItem(
            self, "Изменение типа",
            f"Новый тип для столбца '{column}':",
            types, 0, False
        )

        if not ok or not new_type:
            return

        if "----------" in new_type:
            QMessageBox.warning(self, "Ошибка", "Выберите конкретный тип данных")
            return

        success, error = self.controller.alter_column_type(self.table_name, column, new_type)
        if success:
            QMessageBox.information(self, "Успех", f"Тип столбца '{column}' изменен на {new_type}")
        else:
            QMessageBox.critical(self, "Ошибка", f"Не удалось изменить тип столбца:\n{error}")

    def set_constraint(self):
        """Установка ограничения на столбец (добавлен FOREIGN KEY)."""
        column = self.get_current_column()
        if not self._ensure_column_selected():
            return

        constraints = ["NOT NULL", "UNIQUE", "CHECK", "FOREIGN KEY"]
        constraint, ok = QInputDialog.getItem(
            self, "Установка ограничения",
            f"Выберите тип ограничения для '{column}':",
            constraints, 0, False
        )
        if not ok:
            return

        constraint_value = None
        ref_table = None
        ref_column = None

        if constraint == "CHECK":
            constraint_value, ok = QInputDialog.getText(
                self, "Условие CHECK",
                f"Введите условие CHECK для '{column}':\n(например: {column} > 0)"
            )
            if not ok or not constraint_value:
                return
        elif constraint == "FOREIGN KEY":
            ref_table, ok = QInputDialog.getText(
                self, "FOREIGN KEY - таблица",
                "Введите имя связанной таблицы (REFERENCES table):"
            )
            if not ok or not ref_table:
                return
            ref_column, ok = QInputDialog.getText(
                self, "FOREIGN KEY - столбец",
                "Введите имя связанного столбца (REFERENCES table(column)):"
            )
            if not ok or not ref_column:
                return

        success, error = self.controller.set_constraint(
            self.table_name, column, constraint, constraint_value if constraint != "FOREIGN KEY" else (ref_table, ref_column)
        )

        if success:
            QMessageBox.information(self, "Успех",
                                    f"Ограничение {constraint} установлено на столбец '{column}'")
        else:
            QMessageBox.critical(self, "Ошибка", f"Не удалось установить ограничение:\n{error}")


    def drop_constraint(self):
        """Снятие ограничения со столбца (добавлен FOREIGN KEY)."""
        column = self.get_current_column()
        if not self._ensure_column_selected():
            return

        constraints = ["NOT NULL", "UNIQUE", "CHECK", "FOREIGN KEY"]
        constraint, ok = QInputDialog.getItem(
            self, "Снятие ограничения",
            f"Выберите тип ограничения для снятия с '{column}':",
            constraints, 0, False
        )
        if not ok:
            return

        success, error = self.controller.drop_constraint(self.table_name, column, constraint)
        if success:
            QMessageBox.information(self, "Успех",
                                    f"Ограничение {constraint} снято со столбца '{column}'")
        else:
            QMessageBox.critical(self, "Ошибка", f"Не удалось снять ограничение:\n{error}")


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


class AddRecordDialog(QDialog):
    """Диалог добавления новой записи с улучшенным интерфейсом."""
    def __init__(self, controller, table_name, columns_info, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.table_name = table_name
        self.columns_info = columns_info
        self.field_widgets = {}

        self.setWindowTitle("Добавить запись")
        self.setMinimumWidth(500)
        self.setup_ui()
        self.center_on_screen()

    def center_on_screen(self):
        """Центрирование диалога на экране."""
        screen = self.screen().geometry()
        self.move(screen.center() - self.rect().center())

    def setup_ui(self):
        """Настройка UI с улучшенным дизайном."""
        layout = QFormLayout(self)

        label_style = "color: #333333; font-weight: bold;"

        for col in self.columns_info:
            if 'serial' in col.get('type', '').lower() or 'nextval' in str(col.get('default', '')).lower():
                continue

            col_name = col['name']
            col_type = col.get('type', '').lower()
            is_nullable = col.get('nullable', True)

            label = QLabel(f"{col_name}:")
            label.setStyleSheet(label_style)
            if not is_nullable:
                label.setText(f"{col_name} *")

            widget = self.create_widget_for_type(col_type, col)
            self.field_widgets[col_name] = widget

            if col.get('default') and hasattr(widget, 'setPlaceholderText'):
                widget.setPlaceholderText(f"По умолчанию: {col['default']}")

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
        """Создание виджета по типу с фирменным стилем."""
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
            min-height: 24px;
        }}
        QSpinBox:focus, QDoubleSpinBox:focus, QTimeEdit:focus, QDateEdit:focus {{
            border: 1px solid {blue};
        }}
        QSpinBox::up-button, QDoubleSpinBox::up-button {{
            background-color: #e8e8e8;
            width: 18px;
            border: none;
            border-left: 1px solid #c0c0c0;
            border-top-right-radius: 3px;
            border-bottom: 1px solid #c0c0c0;
        }}
        QSpinBox::down-button, QDoubleSpinBox::down-button {{
            background-color: #e8e8e8;
            width: 18px;
            border: none;
            border-left: 1px solid #c0c0c0;
            border-bottom-right-radius: 3px;
        }}
        QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover {{
            background-color: #d0e8ff;
        }}
        QSpinBox::up-button:pressed, QDoubleSpinBox::up-button:pressed {{
            background-color: {blue};
        }}
        QDateEdit::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 20px;
            border-left: 1px solid #c0c0c0;
            background: {blue};
            border-top-right-radius: 4px;
            border-bottom-right-radius: 4px;
        }}
        QDateEdit::down-arrow {{
            image: none;
            width: 10px; height: 10px;
            background: white;
            border-radius: 5px;
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
            border: 1px solid {blue};
        }}
        QCheckBox::indicator:checked {{
            background-color: {blue};
            border: 1px solid {blue_dark};
            image: none;
        }}
        """

        calendar_style = f"""
        QCalendarWidget QWidget#qt_calendar_navigationbar {{
            background-color: {blue};
            color: white;
            border: none;
        }}
        QCalendarWidget QToolButton {{
            color: white;
            background: transparent;
            margin: 2px;
            border-radius: 4px;
            padding: 4px 8px;
        }}
        QCalendarWidget QToolButton:hover {{
            background-color: {blue_hover};
        }}
        QCalendarWidget QTableView {{
            selection-background-color: {blue};
            selection-color: white;
            outline: none;
        }}
        QCalendarWidget QTableView:item:hover {{
            background: #d0e8ff;
        }}
        QCalendarWidget QHeaderView::section {{
            background-color: #e0e0e0;
            color: #333333;
            padding: 4px;
            border: 1px solid #c0c0c0;
            font-weight: bold;
        }}
        """

        if 'int' in col_type or 'serial' in col_type:
            w = QSpinBox()
            w.setRange(-2147483648, 2147483647)
            w.setStyleSheet(spin_style)
            return w
        elif any(t in col_type for t in ['numeric', 'decimal', 'real', 'double']):
            w = QDoubleSpinBox()
            w.setRange(-999999999.99, 999999999.99)
            w.setDecimals(2)
            w.setStyleSheet(spin_style)
            return w
        elif 'bool' in col_type:
            w = QCheckBox()
            w.setStyleSheet(checkbox_style)
            return w
        elif 'date' in col_type:
            w = QDateEdit()
            w.setDate(QDate.currentDate())
            w.setCalendarPopup(True)
            w.setStyleSheet(spin_style)
            cal = w.calendarWidget()
            if cal:
                cal.setStyleSheet(calendar_style)
            return w
        elif 'timestamp' in col_type or 'time' in col_type:
            w = QTimeEdit()
            w.setTime(QTime.currentTime())
            w.setStyleSheet(spin_style)
            return w
        elif any(t in col_type for t in ['text', 'varchar', 'char']):
            w = ValidatedLineEdit(self.controller)
            w.setStyleSheet("""
                QLineEdit {
                    background-color: white;
                    color: #333333;
                    border: 1px solid #c0c0c0;
                    padding: 4px;
                    min-width: 120px;
                    border-radius: 4px;
                }
                QLineEdit:focus {
                    border: 1px solid #4a86e8;
                }
            """)
            return w
        else:
            # для пользовательских типов (enum, composite) вводим как текст
            w = ValidatedLineEdit(self.controller)
            w.setStyleSheet("""
                QLineEdit {
                    background-color: white;
                    color: #333333;
                    border: 1px solid #c0c0c0;
                    padding: 4px;
                    min-width: 120px;
                    border-radius: 4px;
                }
                QLineEdit:focus {
                    border: 1px solid #4a86e8;
                }
            """)
            return w

    def get_widget_value(self, widget, col_type):
        """Получение значения из виджета."""
        if isinstance(widget, QSpinBox):
            return widget.value()
        elif isinstance(widget, QDoubleSpinBox):
            return widget.value()
        elif isinstance(widget, QCheckBox):
            return widget.isChecked()
        elif isinstance(widget, QDateEdit):
            if 'timestamp' in col_type.lower():
                date = widget.date().toPython()
                return date.strftime('%Y-%m-%d %H:%M:%S')
            else:
                return widget.date().toPython()
        elif isinstance(widget, QTimeEdit):
            return widget.time().toString("HH:mm:ss")
        else:
            return widget.text().strip()

    def validate_and_accept(self):
        """Валидация и сохранение."""
        data = {}
        errors = []

        for col in self.columns_info:
            col_name = col['name']
            col_type = col.get('type', '').lower()
            is_nullable = col.get('nullable', True)
            widget = self.field_widgets.get(col_name)

            if not widget:
                continue

            value = self.get_widget_value(widget, col_type)

            if not value and not is_nullable:
                errors.append(f"Поле '{col_name}' обязательно для заполнения")

            if value:
                data[col_name] = value

        if errors:
            QMessageBox.warning(self, "Ошибка валидации", "\n".join(errors))
            return

        if not data:
            QMessageBox.warning(self, "Ошибка", "Заполните хотя бы одно поле")
            return

        success, error = self.controller.insert_row(self.table_name, data)

        if success:
            QMessageBox.information(self, "Успех", "Запись успешно добавлена")
            self.accept()
        else:
            QMessageBox.critical(self, "Ошибка", f"Не удалось добавить запись:\n{error}")


class EditRecordDialog(QDialog):
    """Диалог редактирования записи с улучшенным интерфейсом."""
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
        """Центрирование диалога на экране."""
        screen = self.screen().geometry()
        self.move(screen.center() - self.rect().center())

    def setup_ui(self):
        """Настройка UI с улучшенным дизайном."""
        layout = QFormLayout(self)

        label_style = "color: #333333; font-weight: bold;"

        for col in self.columns_info:
            col_name = col['name']
            col_type = col.get('type', '').lower()
            is_nullable = col.get('nullable', True)

            label = QLabel(f"{col_name}:")
            label.setStyleSheet(label_style)
            if not is_nullable:
                label.setText(f"{col_name} *")

            widget = self.create_widget_for_type(col_type, col)
            self.field_widgets[col_name] = widget

            if col_name in self.current_data:
                self.set_widget_value(widget, self.current_data[col_name], col_type)

            if col_name == self.columns_info[0]['name']:
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
        QSpinBox::up-button, QDoubleSpinBox::up-button, QTimeEdit::up-button, QDateEdit::up-button {{
            background-color: #e8e8e8;
            width: 18px;
            border: none;
            border-left: 1px solid #c0c0c0;
            border-top-right-radius: 4px;
        }}
        QSpinBox::down-button, QDoubleSpinBox::down-button, QTimeEdit::down-button, QDateEdit::down-button {{
            background-color: #e8e8e8;
            width: 18px;
            border: none;
            border-left: 1px solid #c0c0c0;
            border-bottom-right-radius: 4px;
        }}
        QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover, QTimeEdit::up-button:hover, QDateEdit::up-button:hover,
        QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover, QTimeEdit::down-button:hover, QDateEdit::down-button:hover {{
            background-color: #d0e8ff;
        }}
        QSpinBox::up-button:pressed, QDoubleSpinBox::up-button:pressed, QTimeEdit::up-button:pressed, QDateEdit::up-button:pressed,
        QSpinBox::down-button:pressed, QDoubleSpinBox::down-button:pressed, QTimeEdit::down-button:pressed, QDateEdit::down-button:pressed {{
            background-color: {blue};
        }}
        QDateEdit::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 22px;
            border-left: 1px solid #c0c0c0;
            background: {blue};
            border-top-right-radius: 4px;
            border-bottom-right-radius: 4px;
        }}
        QDateEdit::down-arrow {{
            image: none;
            width: 10px; height: 10px;
            background: white;
            border-radius: 5px;
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
        QCheckBox::indicator:checked:hover {{
            background-color: {blue_hover};
        }}
        """

        calendar_style = f"""
        QCalendarWidget QWidget#qt_calendar_navigationbar {{
            background-color: {blue};
            color: white;
            border: none;
        }}
        QCalendarWidget QToolButton {{
            color: white;
            background: transparent;
            margin: 2px;
            border-radius: 4px;
            padding: 4px 8px;
        }}
        QCalendarWidget QToolButton:hover {{
            background-color: {blue_hover};
        }}
        QCalendarWidget QTableView {{
            selection-background-color: {blue};
            selection-color: white;
            outline: none;
        }}
        QCalendarWidget QTableView:item:hover {{
            background: #d0e8ff;
        }}
        QCalendarWidget QHeaderView::section {{
            background-color: #e0e0e0;
            color: #333333;
            padding: 4px;
            border: 1px solid #c0c0c0;
            font-weight: bold;
        }}
        """

        if 'int' in col_type or 'serial' in col_type:
            w = QSpinBox()
            w.setRange(-2147483648, 2147483647)
            w.setStyleSheet(spin_style)
            return w
        elif any(t in col_type for t in ['numeric', 'decimal', 'real', 'double']):
            w = QDoubleSpinBox()
            w.setRange(-999999999.99, 999999999.99)
            w.setDecimals(2)
            w.setStyleSheet(spin_style)
            return w
        elif 'bool' in col_type:
            w = QCheckBox()
            w.setStyleSheet(checkbox_style)
            return w
        elif 'date' in col_type:
            w = QDateEdit()
            w.setCalendarPopup(True)
            w.setStyleSheet(spin_style)
            cal = w.calendarWidget()
            if cal:
                cal.setStyleSheet(calendar_style)
            return w
        elif 'timestamp' in col_type:
            w = QDateEdit()
            w.setCalendarPopup(True)
            w.setStyleSheet(spin_style)
            cal = w.calendarWidget()
            if cal:
                cal.setStyleSheet(calendar_style)
            return w
        elif 'time' in col_type:
            w = QTimeEdit()
            w.setStyleSheet(spin_style)
            return w
        elif any(t in col_type for t in ['text', 'varchar', 'char']):
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
        else:
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

    def set_widget_value(self, widget, value, col_type):
        """Установка значения в виджет."""
        if value is None:
            return

        try:
            if isinstance(widget, QSpinBox):
                widget.setValue(int(value))
            elif isinstance(widget, QDoubleSpinBox):
                widget.setValue(float(value))
            elif isinstance(widget, QCheckBox):
                widget.setChecked(bool(value))
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

    def get_widget_value(self, widget, col_type):
        """Получение значения из виджета."""
        if isinstance(widget, QSpinBox):
            return widget.value()
        elif isinstance(widget, QDoubleSpinBox):
            return widget.value()
        elif isinstance(widget, QCheckBox):
            return widget.isChecked()
        elif isinstance(widget, QDateEdit):
            if 'timestamp' in col_type.lower():
                date = widget.date().toPython()
                return date.strftime('%Y-%m-%d %H:%M:%S')
            else:
                return widget.date().toPython()
        elif isinstance(widget, QTimeEdit):
            return widget.time().toString("HH:mm:ss")
        else:
            return widget.text().strip()

    def validate_and_accept(self):
        """Валидация и сохранение изменений."""
        first_col = self.columns_info[0]['name']
        where_value = self.get_widget_value(self.field_widgets[first_col], self.columns_info[0].get('type', '').lower())

        data = {}
        errors = []

        for col in self.columns_info:
            if col['name'] == first_col:
                continue

            col_name = col['name']
            col_type = col.get('type', '').lower()
            is_nullable = col.get('nullable', True)
            widget = self.field_widgets[col_name]

            value = self.get_widget_value(widget, col_type)

            if not value and not is_nullable:
                errors.append(f"Поле '{col_name}' обязательно для заполнения")

            if value:
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


class GroupFilterDialog(QDialog):
    """Диалог группировки и фильтрации данных (устаревший для сортировки; без LIKE в WHERE)."""
    def __init__(self, controller, table_name, columns_info, selected_column, cell_value="", is_join_mode=False, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.table_name = table_name
        self.columns_info = columns_info
        self.selected_column = selected_column
        self.cell_value = cell_value
        self.is_join_mode = is_join_mode

        self.where_clause = None
        self.order_clause = None  # сортировка перенесена в отдельное окно
        self.group_clause = None
        self.having_clause = None

        self.setWindowTitle(f"Группировка и фильтрация по столбцу: {selected_column}")
        self.setMinimumWidth(500)
        self.setup_ui()
        self.center_on_screen()

    def center_on_screen(self):
        screen = self.screen().geometry()
        self.move(screen.center() - self.rect().center())

    def setup_ui(self):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(f"<h3>Группировка и фильтрация по столбцу: {self.selected_column}</h3>"))

        form_layout = QFormLayout()

        # Фильтрация (WHERE)
        filter_group = QGroupBox("Фильтрация (WHERE)")
        filter_layout = QVBoxLayout(filter_group)

        where_layout = QHBoxLayout()
        where_layout.addWidget(QLabel("Столбец:"))
        self.where_column_edit = QLineEdit(self.selected_column)
        where_layout.addWidget(self.where_column_edit)

        self.where_operator_combo = QComboBox()
        self.where_operator_combo.setMinimumWidth(150)
        self.where_operator_combo.view().setMinimumWidth(180)
        # LIKE отсутствует — реализован в окне поиска
        self.where_operator_combo.addItems(["=", "!=", "<", "<=", ">", ">=", "IN", "IS NULL", "IS NOT NULL"])
        where_layout.addWidget(self.where_operator_combo)

        self.where_value_edit = QLineEdit()
        if self.cell_value:
            self.where_value_edit.setText(self.cell_value)
        where_layout.addWidget(self.where_value_edit)
        filter_layout.addLayout(where_layout)

        self.where_operator_combo.currentTextChanged.connect(self.update_where_ui)
        layout.addWidget(filter_group)

        # Группировка (GROUP BY)
        group_group = QGroupBox("Группировка (GROUP BY)")
        group_group.setStyleSheet("QGroupBox{color:#000000;}")
        group_layout = QVBoxLayout(group_group)

        self.group_check = QCheckBox(f"Группировать по столбцу: {self.selected_column}")
        self.group_check.setStyleSheet("color:#000000;")
        group_layout.addWidget(self.group_check)

        having_layout = QHBoxLayout()
        having_layout.addWidget(QLabel("HAVING:"))
        self.having_function_combo = QComboBox()
        self.having_function_combo.setMinimumWidth(140)
        self.having_function_combo.view().setMinimumWidth(180)
        self.having_function_combo.addItems(["COUNT", "SUM", "AVG", "MIN", "MAX"])
        self.having_function_combo.setMinimumWidth(140)
        having_layout.addWidget(self.having_function_combo)

        having_layout.addWidget(QLabel("(*)"))

        self.having_operator_combo = QComboBox()
        self.having_operator_combo.addItems(["=", "!=", "<", "<=", ">", ">="])
        self.having_operator_combo.setMinimumWidth(120)
        self.having_operator_combo.view().setMinimumWidth(150)
        having_layout.addWidget(self.having_operator_combo)

        self.having_value_edit = QLineEdit()
        having_layout.addWidget(self.having_value_edit)

        group_layout.addLayout(having_layout)
        layout.addWidget(group_group)

        layout.addStretch()

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_dialog)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.update_where_ui(self.where_operator_combo.currentText())

    def update_where_ui(self, operator_text):
        if operator_text in ["IS NULL", "IS NOT NULL"]:
            self.where_value_edit.setVisible(False)
        else:
            self.where_value_edit.setVisible(True)

    def accept_dialog(self):
        # WHERE
        if self.where_operator_combo.currentText() in ["IS NULL", "IS NOT NULL"]:
            self.where_clause = f"{self.where_column_edit.text()} {self.where_operator_combo.currentText()}"
        else:
            if self.where_value_edit.text().strip():
                op = self.where_operator_combo.currentText()
                if op == "IN":
                    values = [f"'{v.strip()}'" for v in self.where_value_edit.text().split(",")]
                    value = f"({', '.join(values)})"
                else:
                    try:
                        float(self.where_value_edit.text())
                        value = self.where_value_edit.text()
                    except ValueError:
                        value = f"'{self.where_value_edit.text()}'"
                self.where_clause = f"{self.where_column_edit.text()} {op} {value}"
            else:
                self.where_clause = None

        # GROUP BY / HAVING
        if self.group_check.isChecked():
            self.group_clause = self.selected_column
            if self.having_value_edit.text().strip():
                func = self.having_function_combo.currentText()
                op = self.having_operator_combo.currentText()
                value = self.having_value_edit.text()
                self.having_clause = f"{func}(*) {op} {value}"
            else:
                self.having_clause = None
        else:
            self.group_clause = None
            self.having_clause = None

        # Сортировка отсутствует в этом окне
        self.order_clause = None

        self.accept()


class SearchDialog(QDialog):
    """Диалог поиска по таблице с защитой от SQL Injection и SIMILAR TO."""
    def __init__(self, controller, table_name, columns_info, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.table_name = table_name
        self.columns_info = columns_info
        self.search_condition = None
        self.search_params = []
        self.setWindowTitle("Поиск")
        self.setMinimumWidth(500)
        self.setup_ui()
        self.center_on_screen()

    def center_on_screen(self):
        screen = self.screen().geometry()
        self.move(screen.center() - self.rect().center())

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h3>Поиск по таблице</h3>"))

        checkbox_style = """
                QCheckBox { color: #333333; }
                QCheckBox::indicator {
                    width: 14px; height: 14px;
                    border: 1px solid #c0c0c0; border-radius: 3px; background: white;
                }
                QCheckBox::indicator:checked {
                    background-color: #4a86e8; border: 1px solid #2a66c8;
                }
                """

        form_layout = QFormLayout()
        self.column_combo = QComboBox()
        self.column_combo.setMinimumWidth(200)
        self.column_combo.view().setMinimumWidth(250)
        self.column_combo.addItems([col['name'] for col in self.columns_info])
        form_layout.addRow("Столбец:", self.column_combo)

        self.search_type_combo = QComboBox()
        self.search_type_combo.setMinimumWidth(220)
        self.search_type_combo.view().setMinimumWidth(260)
        self.search_type_combo.addItems([
            "LIKE (шаблонный поиск)",
            "~ (регулярка)",
            "~* (регулярка без учета регистра)",
            "!~ (не соответствует)",
            "!~* (не соответствует без учета регистра)",
            "= (точное совпадение)"
        ])
        form_layout.addRow("Тип поиска:", self.search_type_combo)

        self.search_text = QLineEdit()
        self.search_text.setPlaceholderText("Введите текст для поиска...")
        form_layout.addRow("Текст:", self.search_text)

        layout.addLayout(form_layout)

        hint_label = QLabel(
            "<i><b>Подсказка:</b><br>"
            "• LIKE: используйте % (пример: %текст%)<br>"
            "• ~: POSIX регулярное выражение<br>"
            "• ~*: регулярка без учета регистра</i>"
        )
        hint_label.setWordWrap(True)
        layout.addWidget(hint_label)

        # SIMILAR TO
        self.regex_group = QGroupBox("SIMILAR TO")
        regex_layout = QVBoxLayout(self.regex_group)
        self.regex_column_combo = QComboBox()
        self.regex_column_combo.setMinimumWidth(200)
        self.regex_column_combo.view().setMinimumWidth(250)
        self.regex_pattern_edit = QLineEdit()
        self.regex_pattern_edit.setPlaceholderText("Шаблон (например: '(Р|Г)%')")
        self.regex_not_checkbox = QCheckBox("NOT SIMILAR TO")
        self.regex_not_checkbox.setStyleSheet(checkbox_style)

        cols = [c['name'] for c in self.controller.get_table_columns(self.table_name)]
        self.regex_column_combo.addItems(cols)
        regex_layout.addWidget(QLabel("Столбец"))
        regex_layout.addWidget(self.regex_column_combo)
        regex_layout.addWidget(QLabel("Шаблон"))
        regex_layout.addWidget(self.regex_pattern_edit)
        regex_layout.addWidget(self.regex_not_checkbox)
        layout.addWidget(self.regex_group)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_dialog)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept_dialog(self):
        # SIMILAR TO (парам. вариант)
        pattern = self.regex_pattern_edit.text().strip()
        if pattern:
            col = self.regex_column_combo.currentText()
            not_part = "NOT " if self.regex_not_checkbox.isChecked() else ""
            self.search_condition = f"{col} {not_part}SIMILAR TO %s"
            self.search_params = [pattern]
            self.accept()
            return

        # обычный поиск
        column = self.column_combo.currentText()
        search_text = self.search_text.text().strip()
        if not search_text:
            QMessageBox.warning(self, "Ошибка", "Введите текст для поиска или заполните блок SIMILAR TO")
            return

        st = self.search_type_combo.currentText()
        if "LIKE" in st:
            self.search_condition = f"{column} LIKE %s"
            self.search_params = [f"%{search_text}%"]
        elif "~*" in st and "!" in st:
            self.search_condition = f"{column} !~* %s"
            self.search_params = [search_text]
        elif "~*" in st:
            self.search_condition = f"{column} ~* %s"
            self.search_params = [search_text]
        elif "!~" in st:
            self.search_condition = f"{column} !~ %s"
            self.search_params = [search_text]
        elif "~" in st:
            self.search_condition = f"{column} ~ %s"
            self.search_params = [search_text]
        else:
            self.search_condition = f"{column} = %s"
            self.search_params = [search_text]

        self.accept()


class TypeManagementDialog(QDialog):
    """
    Компактный диалог управления типами данных:
    - слева список типов (фильтр: все / enum / composite)
    - двойной клик по типу открывает окно редактирования конкретного типа
    - внизу мини-форма для создания нового типа (ENUM или составной)
    """
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.setWindowTitle("Типы данных")
        self.setMinimumWidth(800)
        self.setMinimumHeight(520)
        self.setup_ui()
        self.refresh_types()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)

        # Верхняя панель фильтра
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Показать:"))
        self.type_filter_combo = QComboBox()
        self.type_filter_combo.setMinimumWidth(160)
        self.type_filter_combo.view().setMinimumWidth(200)
        self.type_filter_combo.addItems(["Все", "ENUM", "Составные"])
        filter_layout.addWidget(self.type_filter_combo)
        filter_layout.addStretch()
        main_layout.addLayout(filter_layout)

        # Центральная часть: список типов + панель подсказки
        center_layout = QHBoxLayout()
        self.types_list = QListWidget()
        self.types_list.setMinimumWidth(260)
        center_layout.addWidget(self.types_list)

        self.hint_label = QLabel(
            "<b>Советы:</b><br>"
            "• Двойной клик по ENUM — редактирование значений<br>"
            "• Двойной клик по составному типу — редактирование атрибутов"
        )
        self.hint_label.setWordWrap(True)
        center_layout.addWidget(self.hint_label)
        main_layout.addLayout(center_layout)

        # Нижняя панель создания (переработано для составных типов)
        new_group = QGroupBox("Создание нового типа")
        new_layout = QVBoxLayout(new_group)

        top_row = QFormLayout()
        self.new_type_kind = QComboBox()
        self.new_type_kind.setMinimumWidth(120)
        self.new_type_kind.view().setMinimumWidth(160)
        self.new_type_kind.addItems(["ENUM", "Составной"])
        top_row.addRow("Тип:", self.new_type_kind)

        self.new_type_name = QLineEdit()
        self.new_type_name.setPlaceholderText("Имя типа (имя идентификатора)")
        top_row.addRow("Имя:", self.new_type_name)
        new_layout.addLayout(top_row)

        # Для ENUM — строка значений через запятую
        self.new_enum_values = QLineEdit()
        self.new_enum_values.setPlaceholderText("Значения ENUM через запятую (например: low,medium,high)")
        new_layout.addWidget(QLabel("Значения ENUM:"))
        new_layout.addWidget(self.new_enum_values)

        # Для составного — отдельный мини‑конструктор полей
        self.composite_fields_group = QGroupBox("Поля составного типа")
        self.composite_fields_group.setVisible(False)
        comp_outer_layout = QVBoxLayout(self.composite_fields_group)

        self.comp_fields_layout = QVBoxLayout()
        comp_outer_layout.addLayout(self.comp_fields_layout)

        add_field_btn = QPushButton("Добавить поле")
        add_field_btn.clicked.connect(self.add_composite_field_row)
        comp_outer_layout.addWidget(add_field_btn)

        new_layout.addWidget(self.composite_fields_group)

        self.create_type_btn = QPushButton("Создать тип")
        new_layout.addWidget(self.create_type_btn)

        new_hint = QLabel(
            "<i>Подсказка для составного типа:</i><br>"
            "• Введите имя поля и выберите тип данных из списка.<br>"
            "• Можно добавить несколько полей кнопкой «Добавить поле»."
        )
        new_hint.setWordWrap(True)
        new_layout.addWidget(new_hint)

        main_layout.addWidget(new_group)

        # Кнопки
        btn_bar = QHBoxLayout()
        self.refresh_btn = QPushButton("Обновить")
        self.delete_btn = QPushButton("Удалить выбранный тип")
        close_btn = QPushButton("Закрыть")
        btn_bar.addWidget(self.refresh_btn)
        btn_bar.addWidget(self.delete_btn)
        btn_bar.addStretch()
        btn_bar.addWidget(close_btn)
        main_layout.addLayout(btn_bar)

        # Сигналы
        self.type_filter_combo.currentTextChanged.connect(self.refresh_types)
        self.types_list.itemDoubleClicked.connect(self.open_type_editor)
        self.create_type_btn.clicked.connect(self.create_type)
        self.refresh_btn.clicked.connect(self.refresh_types)
        self.delete_btn.clicked.connect(self.delete_selected_type)
        close_btn.clicked.connect(self.accept)
        self.new_type_kind.currentTextChanged.connect(self._toggle_composite_ui)

        # инициализация для составных: один ряд полей по умолчанию
        self.add_composite_field_row()

    def _toggle_composite_ui(self, kind_text: str):
        is_comp = (kind_text == "Составной")
        self.composite_fields_group.setVisible(is_comp)
        self.new_enum_values.setEnabled(not is_comp)

    def add_composite_field_row(self):
        """Добавляет строку для ввода одного поля составного типа."""
        row = QHBoxLayout()
        name_edit = QLineEdit()
        name_edit.setPlaceholderText("имя_поля")
        type_combo = QComboBox()
        type_combo.setMinimumWidth(140)
        type_combo.view().setMinimumWidth(200)
        type_combo.addItems([
            "INTEGER", "BIGINT", "NUMERIC", "TEXT", "VARCHAR(100)", "VARCHAR(200)",
            "BOOLEAN", "DATE", "TIMESTAMP"
        ])
        # возможность ввода своего типа (в т.ч. enum)
        type_combo.setEditable(True)

        remove_btn = QPushButton("−")
        remove_btn.setFixedWidth(28)

        def remove_row():
            # удаляем виджеты и layout
            for w in (name_edit, type_combo, remove_btn):
                w.setParent(None)
                w.deleteLater()
            # удалить сам layout из контейнера
            idx = -1
            for i in range(self.comp_fields_layout.count()):
                if self.comp_fields_layout.itemAt(i).layout() is row:
                    idx = i
                    break
            if idx >= 0:
                item = self.comp_fields_layout.takeAt(idx)
                del item

        remove_btn.clicked.connect(remove_row)

        row.addWidget(QLabel("Имя:"))
        row.addWidget(name_edit)
        row.addWidget(QLabel("Тип:"))
        row.addWidget(type_combo)
        row.addWidget(remove_btn)

        self.comp_fields_layout.addLayout(row)

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
        kind, name = (None, None)
        text = item.text()
        if text.startswith("ENUM: "):
            kind, name = "ENUM", text.split("ENUM: ", 1)[1]
        elif text.startswith("COMPOSITE: "):
            kind, name = "COMPOSITE", text.split("COMPOSITE: ", 1)[1]

        if not kind or not name:
            return

        if kind == "ENUM":
            dlg = EnumEditorDialog(self.controller, name, self)
            dlg.exec_()
        else:
            dlg = CompositeEditorDialog(self.controller, name, self)
            dlg.exec_()

        self.refresh_types()

    def create_type(self):
        kind = self.new_type_kind.currentText()
        name = self.new_type_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Укажите имя типа")
            return

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
            # собираем поля из строк конструктора
            cols = []
            for i in range(self.comp_fields_layout.count()):
                item = self.comp_fields_layout.itemAt(i)
                row = item.layout()
                if not row:
                    continue
                # ожидаем структуру: QLabel, name_edit, QLabel, type_combo, remove_btn
                name_edit = None
                type_combo = None
                for j in range(row.count()):
                    w = row.itemAt(j).widget()
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
                # очищаем поля
                while self.comp_fields_layout.count():
                    item = self.comp_fields_layout.takeAt(0)
                    if item.layout():
                        # удаляем вложенный layout
                        lay = item.layout()
                        while lay.count():
                            witem = lay.takeAt(0)
                            w = witem.widget()
                            if w:
                                w.setParent(None)
                                w.deleteLater()
                    del item
                self.add_composite_field_row()
                self.refresh_types()
            else:
                QMessageBox.critical(self, "Ошибка", msg)

    def delete_selected_type(self):
        kind, name = self.parse_selected_type()
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


class EnumEditorDialog(QDialog):
    """Небольшое окно для редактирования значений ENUM (разделено по вкладкам)."""
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

        # Вкладка "Просмотр"
        view_tab = QWidget()
        v_layout = QVBoxLayout(view_tab)
        self.values_list = QListWidget()
        v_layout.addWidget(self.values_list)
        self.tabs.addTab(view_tab, "Просмотр")

        # Вкладка "Добавить"
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

        # Вкладка "Переименовать"
        ren_tab = QWidget()
        r_layout = QFormLayout(ren_tab)
        self.old_val_edit = QLineEdit()
        self.new_val_edit = QLineEdit()
        r_layout.addRow("Старое значение:", self.old_val_edit)
        r_layout.addRow("Новое значение:", self.new_val_edit)
        ren_btn = QPushButton("Переименовать значение")
        ren_btn.clicked.connect(self.on_rename_value)
        r_layout.addRow(ren_btn)
        self.tabs.addTab(ren_tab, "Переименовать")

        # Низ диалога
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
        new_val = self.new_val_edit.text().strip()
        if not old_val or not new_val:
            QMessageBox.warning(self, "Ошибка", "Заполните оба значения")
            return
        ok, msg = self.controller.rename_enum_value(self.type_name, old_val, new_val)
        if ok:
            QMessageBox.information(self, "Успех", "Значение переименовано")
            self.old_val_edit.clear()
            self.new_val_edit.clear()
            self.refresh_values()
            self.tabs.setCurrentIndex(0)
        else:
            QMessageBox.critical(self, "Ошибка", msg)


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

        # Добавить
        add_group = QGroupBox("Добавить атрибут")
        add_form = QFormLayout(add_group)
        self.add_name = QLineEdit()
        self.add_type = QLineEdit()
        self.add_type.setPlaceholderText("INTEGER, TEXT, my_enum и т.д.")
        add_form.addRow("Имя:", self.add_name)
        add_form.addRow("Тип:", self.add_type)

        # Удалить
        del_group = QGroupBox("Удалить атрибут")
        del_form = QFormLayout(del_group)
        self.del_name = QLineEdit()
        del_form.addRow("Имя:", self.del_name)

        # Переименовать
        ren_group = QGroupBox("Переименовать атрибут")
        ren_form = QFormLayout(ren_group)
        self.ren_old = QLineEdit()
        self.ren_new = QLineEdit()
        ren_form.addRow("Старое имя:", self.ren_old)
        ren_form.addRow("Новое имя:", self.ren_new)

        # Изменить тип
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

        # Если уже активен JOIN — подхватываем текущую конфигурацию
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
        """Центрирование диалога на экране."""
        screen = self.screen().geometry()
        self.move(screen.center() - self.rect().center())

    def setup_ui(self):
        """Настройка UI."""
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
        """Выбор основной таблицы."""
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
        """Добавление соединений."""
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
                # Добавляем только столбцы и метки новой таблицы
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
        """Применение строковых функций."""
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
        """Принятие настроек."""
        if not self.selected_table:
            QMessageBox.warning(self, "Ошибка", "Выберите таблицу для вывода")
            return
        self.accept()


class SelectTableDialog(QDialog):
    """Диалог выбора таблицы с отображением и выбором столбцов."""
    def __init__(self, controller, current_table=None, parent=None, task_dialog=None):
        super().__init__(parent)
        self.controller = controller
        self.selected_table = current_table
        self.selected_columns = None
        self.scroll_area = None
        self.task_dialog = task_dialog

        # атрибуты для чекбоксов/скролла
        self.columns_checks = {}
        self.scroll_widget = None
        self.scroll_layout = None

        self.setWindowTitle("Выбрать таблицу")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        self.setup_ui()
        self.center_on_screen()

    def center_on_screen(self):
        """Центрирование диалога на экране."""
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

        # первичное заполнение и подписка на смену таблицы
        self.table_combo.currentTextChanged.connect(self._populate_column_checkboxes)
        self._populate_column_checkboxes(self.table_combo.currentText())

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_dialog)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _clear_layout_safe(self, vlayout):
        """Безопасно очищает layout, не удаляя сам объект layout и не трогая scroll_area."""
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
        """Переиспользует один и тот же контейнер для чекбоксов, предотвращая удаление C++ объектов."""
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

    def on_table_changed(self, table_name):
        """Обработка изменения таблицы (оставлено для совместимости, делегирует на безопасный апдейт)."""
        self._populate_column_checkboxes(table_name)

    def rename_table(self):
        """Переименование таблицы."""
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
                    self.task_dialog.update_table_name(old_name, new_name)

                self._populate_column_checkboxes(new_name)
            else:
                QMessageBox.critical(self, "Ошибка", f"Не удалось переименовать таблицу:\n{error}")

    def accept_dialog(self):
        """Принятие настроек."""
        self.selected_table = self.table_combo.currentText()
        selected = [name for name, check in self.columns_checks.items() if check.isChecked()]
        self.selected_columns = selected if selected else None
        self.accept()


class JoinWizardDialog(QDialog):
    """Мастер создания JOIN запросов."""
    def __init__(self, controller, base_table, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.base_table = base_table
        self.scroll_area = None
        self.join_columns_checks = {}
        self.base_columns_checks = {}

        self.setWindowTitle("Мастер соединений (JOIN)")
        self.setMinimumWidth(780)
        self.setMinimumHeight(600)
        self.setup_ui()
        self.center_on_screen()

    def center_on_screen(self):
        """Центрирование диалога на экране."""
        screen = self.screen().geometry()
        self.move(screen.center() - self.rect().center())

    def setup_ui(self):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(f"<h3>Создание JOIN запроса</h3>"))
        layout.addWidget(QLabel(f"<b>Базовая таблица:</b> {self.base_table}"))

        layout.addWidget(QLabel("<b>Выберите таблицу для соединения:</b>"))

        join_table_layout = QHBoxLayout()
        join_table_layout.addWidget(QLabel("Таблица:"))

        self.join_table_combo = QComboBox()
        self.join_table_combo.setMinimumWidth(200)
        self.join_table_combo.view().setMinimumWidth(240)
        all_tables = self.controller.get_all_tables()
        other_tables = [t for t in all_tables if t != self.base_table]
        self.join_table_combo.addItems(other_tables)

        if 'task2' in other_tables:
            self.join_table_combo.setCurrentText('task2')

        join_table_layout.addWidget(self.join_table_combo)
        layout.addLayout(join_table_layout)

        join_type_layout = QHBoxLayout()
        join_type_layout.addWidget(QLabel("Тип соединения:"))

        self.join_type_combo = QComboBox()
        self.join_type_combo.setMinimumWidth(140)
        self.join_type_combo.view().setMinimumWidth(180)
        self.join_type_combo.addItems(["INNER", "LEFT", "RIGHT", "FULL"])
        join_type_layout.addWidget(self.join_type_combo)
        layout.addLayout(join_type_layout)

        layout.addWidget(QLabel("<b>Условие соединения (ON):</b>"))

        on_layout = QHBoxLayout()

        self.base_column_combo = QComboBox()
        self.base_column_combo.setMinimumWidth(160)
        self.base_column_combo.view().setMinimumWidth(200)
        self.update_base_columns()
        on_layout.addWidget(QLabel(f"{self.base_table}."))
        on_layout.addWidget(self.base_column_combo)

        on_layout.addWidget(QLabel(" = "))

        self.join_column_combo = QComboBox()
        self.join_column_combo.setMinimumWidth(160)
        self.join_column_combo.view().setMinimumWidth(200)
        self.join_table_label = QLabel()
        on_layout.addWidget(self.join_table_label)
        on_layout.addWidget(QLabel("."))
        on_layout.addWidget(self.join_column_combo)

        layout.addLayout(on_layout)

        layout.addWidget(QLabel("<b>Выберите столбцы для вывода:</b>"))

        columns_layout = QHBoxLayout()

        checkbox_style = """
        QCheckBox {
            color: white;
        }
        QCheckBox::indicator {
            width: 14px; height: 14px;
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
        self.checkbox_style = checkbox_style

        # ---- базовая таблица
        base_group = QGroupBox(f"Столбцы таблицы {self.base_table}")
        base_layout = QVBoxLayout(base_group)
        base_scroll = QScrollArea()
        base_scroll.setWidgetResizable(True)
        base_scroll_widget = QWidget()
        base_scroll_layout = QVBoxLayout(base_scroll_widget)

        self.base_columns_checks = {}
        base_columns = self.controller.get_table_columns(self.base_table) or []
        for col in base_columns:
            check = QCheckBox(f"{col['name']}", parent=base_scroll_widget)
            check.setChecked(True)
            check.setLayoutDirection(Qt.LeftToRight)
            check.setStyleSheet(self.checkbox_style)
            self.base_columns_checks[col['name']] = check
            base_scroll_layout.addWidget(check)

        base_scroll_layout.addStretch()
        base_scroll.setWidget(base_scroll_widget)
        base_layout.addWidget(base_scroll)
        columns_layout.addWidget(base_group)

        # ---- присоединяемая таблица
        join_group = QGroupBox(f"Столбцы присоединяемой таблицы")
        join_layout = QVBoxLayout(join_group)
        self.join_scroll = QScrollArea()
        self.join_scroll.setWidgetResizable(True)

        self.join_scroll_widget = QWidget()
        self.join_scroll_layout = QVBoxLayout(self.join_scroll_widget)
        self.join_scroll.setWidget(self.join_scroll_widget)
        join_layout.addWidget(self.join_scroll)
        columns_layout.addWidget(join_group)

        self.join_columns_checks = {}

        # подключаем слот и делаем первичную инициализацию
        self.join_table_combo.currentTextChanged.connect(self._populate_join_checkboxes)
        self._populate_join_checkboxes(self.join_table_combo.currentText())

        layout.addLayout(columns_layout)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _clear_layout_safe(self, vlayout):
        """Безопасно очищает layout, не удаляя сам layout-объект."""
        if vlayout is None:
            return
        while vlayout.count():
            item = vlayout.takeAt(vlayout.count() - 1)
            if item is None:
                continue
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
            child_layout = item.layout()
            if child_layout is not None:
                self._clear_layout_safe(child_layout)

    def _populate_join_checkboxes(self, table_name):
        """Заполняет чекбоксы колонок присоединяемой таблицы, переиспользуя один и тот же layout."""
        if not hasattr(self, "join_scroll_layout") or self.join_scroll_layout is None:
            return

        self._clear_layout_safe(self.join_scroll_layout)
        self.join_columns_checks = {}

        if not table_name:
            self.join_table_label.setText("")
            self.join_column_combo.clear()
            return

        self.join_table_label.setText(table_name)
        join_columns = self.controller.get_table_columns(table_name) or []

        for col in join_columns:
            check = QCheckBox(f"{col['name']}", parent=self.join_scroll_widget)
            check.setChecked(True)
            check.setLayoutDirection(Qt.LeftToRight)
            check.setStyleSheet(self.checkbox_style)
            self.join_columns_checks[col['name']] = check
            self.join_scroll_layout.addWidget(check)

        self.join_scroll_layout.addStretch()

        cur = self.join_column_combo.currentText()
        self.join_column_combo.blockSignals(True)
        self.join_column_combo.clear()
        for col in join_columns:
            self.join_column_combo.addItem(col['name'])
        if cur and cur in [c['name'] for c in join_columns]:
            self.join_column_combo.setCurrentText(cur)
        self.join_column_combo.blockSignals(False)

    def update_base_columns(self):
        """Обновление списка столбцов базовой таблицы."""
        columns = self.controller.get_table_columns(self.base_table)
        self.base_column_combo.clear()
        self.base_column_combo.addItems([col['name'] for col in columns])

    def update_join_columns(self, table_name):
        """Обновление списка столбцов присоединяемой таблицы (без пересоздания виджетов)."""
        if not table_name:
            return
        self._populate_join_checkboxes(table_name)

    def get_join_config(self):
        """Получение конфигурации JOIN."""
        join_table = self.join_table_combo.currentText()
        join_type = self.join_type_combo.currentText()

        base_col = self.base_column_combo.currentText()
        join_col = self.join_column_combo.currentText()

        on_condition = f"{self.base_table}.{base_col} = {join_table}.{join_col}"

        selected_columns = []
        column_labels = []
        column_mapping = {}

        for col_name, check in self.base_columns_checks.items():
            if check.isChecked():
                full_column_name = f"{self.base_table}.{col_name}"
                display_name = f"{self.base_table}_{col_name}"
                selected_columns.append(full_column_name)
                column_labels.append(display_name)
                column_mapping[display_name] = full_column_name

        for col_name, check in self.join_columns_checks.items():
            if check.isChecked():
                full_column_name = f"{join_table}.{col_name}"
                display_name = f"{join_table}_{col_name}"
                selected_columns.append(full_column_name)
                column_labels.append(display_name)
                column_mapping[display_name] = full_column_name

        if not selected_columns:
            selected_columns = [f"{self.base_table}.*", f"{join_table}.*"]
            base_columns = [col['name'] for col in self.controller.get_table_columns(self.base_table)]
            join_columns = [col['name'] for col in self.controller.get_table_columns(join_table)]

            column_labels = []
            for col in base_columns:
                display_name = f"{self.base_table}_{col}"
                column_labels.append(display_name)
                column_mapping[display_name] = f"{self.base_table}.{col}"

            for col in join_columns:
                display_name = f"{join_table}_{col}"
                column_labels.append(display_name)
                column_mapping[display_name] = f"{join_table}.{col}"

        return {
            'tables_info': [
                {'name': self.base_table, 'alias': None}
            ],
            'selected_columns': selected_columns,
            'column_labels': column_labels,
            'column_mapping': column_mapping,
            'join_conditions': [
                {
                    'type': join_type,
                    'table': join_table,
                    'alias': None,
                    'on': on_condition
                }
            ],
            'where': None,
            'order_by': None
        }


class StringFunctionsDialog(QDialog):
    """Диалог работы со строковыми функциями."""
    def __init__(self, controller, table_name, columns_info, parent=None, selected_column=None):
        super().__init__(parent)
        self.controller = controller
        self.table_name = table_name
        self.columns_info = columns_info
        self.selected_column = selected_column
        self.logger = Logger()

        self.setWindowTitle("Строковые функции")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        self.setup_ui()
        self.center_on_screen()

    def center_on_screen(self):
        """Центрирование диалога на экране."""
        screen = self.screen().geometry()
        self.move(screen.center() - self.rect().center())

    def setup_ui(self):
        """Настройка UI."""
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("<h3>Применение строковых функций</h3>"))

        form_layout = QFormLayout()

        self.column_combo = QComboBox()
        self.column_combo.setMinimumWidth(200)
        self.column_combo.view().setMinimumWidth(240)
        string_columns = [col['name'] for col in self.columns_info
                          if 'char' in col.get('type', '').lower() or 'text' in col.get('type', '').lower()]
        if not string_columns:
            string_columns = [col['name'] for col in self.columns_info]
        self.column_combo.addItems(string_columns)

        if self.selected_column and self.selected_column in string_columns:
            self.column_combo.setCurrentText(self.selected_column)

        form_layout.addRow("Столбец:", self.column_combo)

        self.function_combo = QComboBox()
        self.function_combo.setMinimumWidth(240)
        self.function_combo.view().setMinimumWidth(280)
        self.function_combo.addItems([
            "UPPER (верхний регистр)",
            "LOWER (нижний регистр)",
            "SUBSTRING (подстрока)",
            "TRIM (удаление пробелов)",
            "LTRIM (удаление пробелов слева)",
            "RTRIM (удаление пробелов справа)",
            "LPAD (дополнение слева)",
            "RPAD (дополнение справа)",
            "CONCAT (объединение)",
            "LENGTH (длина строки)",
            "INITCAP (первый символ в верхнем регистре)"
        ])
        self.function_combo.currentTextChanged.connect(self.on_function_changed)
        form_layout.addRow("Функция:", self.function_combo)

        layout.addLayout(form_layout)

        self.params_widget = QWidget()
        self.params_layout = QFormLayout(self.params_widget)
        layout.addWidget(self.params_widget)

        layout.addWidget(QLabel("<b>Результат:</b>"))
        self.result_table = QTableWidget()
        self.result_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.result_table)

        buttons_layout = QHBoxLayout()

        apply_btn = QPushButton("Применить функцию")
        apply_btn.clicked.connect(self.apply_function)
        buttons_layout.addWidget(apply_btn)

        self.create_column_btn = QPushButton("Создать столбец с результатом")
        self.create_column_btn.clicked.connect(self.create_column_with_function)
        self.create_column_btn.setEnabled(False)
        buttons_layout.addWidget(self.create_column_btn)

        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(close_btn)

        layout.addLayout(buttons_layout)

        self.on_function_changed(self.function_combo.currentText())

    def on_function_changed(self, function_text):
        """Обработка изменения выбранной функции и параметров."""
        while self.params_layout.rowCount() > 0:
            self.params_layout.removeRow(0)

        if "SUBSTRING" in function_text:
            self.start_pos = QSpinBox()
            self.start_pos.setRange(1, 1000)
            self.start_pos.setValue(1)
            self.params_layout.addRow("Начальная позиция:", self.start_pos)

            self.length = QSpinBox()
            self.length.setRange(1, 1000)
            self.length.setValue(10)
            self.params_layout.addRow("Длина:", self.length)

        elif "LPAD" in function_text or "RPAD" in function_text:
            self.pad_length = QSpinBox()
            self.pad_length.setRange(1, 1000)
            self.pad_length.setValue(20)
            self.params_layout.addRow("Длина:", self.pad_length)

            self.pad_char = QLineEdit()
            self.pad_char.setText(" ")
            self.pad_char.setMaxLength(1)
            self.params_layout.addRow("Символ:", self.pad_char)

        elif "CONCAT" in function_text:
            self.concat_text = QLineEdit()
            self.concat_text.setPlaceholderText("Текст для объединения")
            self.params_layout.addRow("Текст:", self.concat_text)

            self.concat_position = QComboBox()
            self.concat_position.setMinimumWidth(140)
            self.concat_position.view().setMinimumWidth(170)
            self.concat_position.addItems(["В начале", "В конце"])
            self.params_layout.addRow("Позиция:", self.concat_position)

        self.current_function = function_text

    def get_sql_expression(self):
        """Формирование SQL выражения для текущей функции с поддержкой кириллицы."""
        column = self.column_combo.currentText()
        function = self.function_combo.currentText()

        try:
            if "UPPER" in function:
                sql_expr = f"upper(\"{column}\")"
            elif "LOWER" in function:
                sql_expr = f"lower(\"{column}\")"
            elif "INITCAP" in function:
                sql_expr = f"initcap(\"{column}\")"
            elif "SUBSTRING" in function:
                start = self.start_pos.value()
                length = self.length.value()
                sql_expr = f"substring(\"{column}\" FROM {start} FOR {length})"
            elif "LTRIM" in function:
                sql_expr = f"ltrim(\"{column}\")"
            elif "RTRIM" in function:
                sql_expr = f"rtrim(\"{column}\")"
            elif "TRIM" in function:
                sql_expr = f"trim(\"{column}\")"
            elif "LPAD" in function:
                length = self.pad_length.value()
                char = self.pad_char.text() or ' '
                sql_expr = f"lpad(\"{column}\", {length}, '{char}')"
            elif "RPAD" in function:
                length = self.pad_length.value()
                char = self.pad_char.text() or ' '
                sql_expr = f"rpad(\"{column}\", {length}, '{char}')"
            elif "CONCAT" in function:
                text = self.concat_text.text()
                if self.concat_position.currentText() == "В начале":
                    sql_expr = f"concat('{text}', \"{column}\")"
                else:
                    sql_expr = f"concat(\"{column}\", '{text}')"
            elif "LENGTH" in function:
                sql_expr = f"length(\"{column}\")"
            else:
                raise ValueError("Неизвестная функция")

            return sql_expr, column
        except Exception as e:
            self.logger.error(f"Ошибка формирования SQL выражения: {str(e)}")
            return None, None

    def apply_function(self):
        """Применение выбранной функции к данным (предпросмотр)."""
        try:
            sql_expr, column = self.get_sql_expression()
            if not sql_expr:
                QMessageBox.warning(self, "Ошибка", "Не удалось сформировать SQL выражение")
                return

            query = f"SELECT {column} as original, {sql_expr} as result FROM \"{self.table_name}\" LIMIT 20"
            results = self.controller.execute_select(query)

            if results:
                self.result_table.setColumnCount(2)
                self.result_table.setHorizontalHeaderLabels(["Оригинал", "Результат"])
                self.result_table.setRowCount(len(results))

                for row_idx, row_data in enumerate(results):
                    for col_idx, value in enumerate(row_data):
                        str_value = str(value) if value is not None else ""

                        if isinstance(value, (int, float)):
                            item = NumericTableItem(str_value, value)
                        elif isinstance(value, date):
                            item = DateTableItem(str_value, value)
                        elif isinstance(value, datetime):
                            item = TimestampTableItem(str_value, value)
                        elif isinstance(value, bool):
                            item = BooleanTableItem(str_value, value)
                        else:
                            item = QTableWidgetItem(str_value)

                        self.result_table.setItem(row_idx, col_idx, item)

                self.result_table.resizeColumnsToContents()
                self.logger.info(f"Функция {self.function_combo.currentText()} применена успешно")
                self.create_column_btn.setEnabled(True)
            else:
                QMessageBox.information(self, "Результат", "Нет данных для отображения")

        except Exception as e:
            self.logger.error(f"Ошибка применения функции: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Ошибка при применении функции:\n{str(e)}")

    def create_column_with_function(self):
        """Создание нового столбца с результатом применения функции."""
        try:
            sql_expr, orig_column = self.get_sql_expression()
            if not sql_expr:
                QMessageBox.warning(self, "Ошибка", "Не удалось сформировать SQL выражение")
                return

            function_name = self.current_function.split(" ")[0].lower()
            suggested_name = f"{function_name}_{orig_column}"

            new_column_name, ok = QInputDialog.getText(
                self, "Имя нового столбца",
                "Введите имя для нового столбца:",
                text=suggested_name
            )

            if not ok or not new_column_name:
                return

            data_type = "TEXT"
            if "LENGTH" in self.current_function:
                data_type = "INTEGER"

            success, error = self.controller.add_column(
                self.table_name, new_column_name, data_type
            )

            if not success:
                QMessageBox.critical(self, "Ошибка", f"Не удалось добавить столбец:\n{error}")
                return

            update_query = f"UPDATE \"{self.table_name}\" SET \"{new_column_name}\" = {sql_expr}"
            success, error = self.controller.execute_update(update_query)

            if success:
                QMessageBox.information(self, "Успех", f"Столбец '{new_column_name}' успешно создан и заполнен результатами функции.")
                self.logger.info(f"Создан столбец '{new_column_name}' с функцией {self.current_function}")
                self.accept()
                if hasattr(self.parent(), 'accept'):
                    self.parent().accept()
            else:
                self.controller.drop_column(self.table_name, new_column_name)
                QMessageBox.critical(self, "Ошибка", f"Ошибка при заполнении столбца:\n{error}")
                self.logger.error(f"Ошибка при заполнении столбца '{new_column_name}': {error}")

        except Exception as e:
            self.logger.error(f"Ошибка создания столбца: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Ошибка при создании столбца:\n{str(e)}")


class ColumnActionsDialog(QDialog):
    """Окно действий над столбцом."""
    def __init__(self, controller, table_name, columns_info, selected_column, prefill_value="", parent=None):
        super().__init__(parent)
        self.controller = controller
        self.table_name = table_name
        self.columns_info = columns_info
        self.selected_column = selected_column
        self.prefill_value = prefill_value
        self.task_dialog: TaskDialog = parent  # TaskDialog

        self.setWindowTitle(f"Действия над столбцом: {self.selected_column}")
        self.setMinimumWidth(420)
        self.setup_ui()
        self.center_on_screen()

    def center_on_screen(self):
        screen = self.screen().geometry()
        self.move(screen.center() - self.rect().center())

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"<h3>Столбец: {self.selected_column}</h3>"))

        sort_btn = QPushButton("Сортировка")
        sort_btn.setMinimumHeight(36)
        sort_btn.clicked.connect(self.open_sort)
        layout.addWidget(sort_btn)

        filter_btn = QPushButton("Фильтрация (WHERE)")
        filter_btn.setMinimumHeight(36)
        filter_btn.clicked.connect(self.open_filter)
        layout.addWidget(filter_btn)

        group_btn = QPushButton("Группировка (GROUP BY, агрегаты, HAVING)")
        group_btn.setMinimumHeight(36)
        group_btn.clicked.connect(self.open_group)
        layout.addWidget(group_btn)

        subquery_btn = QPushButton("Подзапросы (ANY/ALL/EXISTS)")
        subquery_btn.setMinimumHeight(36)
        subquery_btn.clicked.connect(self.open_subquery_builder)
        layout.addWidget(subquery_btn)

        case_btn = QPushButton("Выражения CASE / COALESCE / NULLIF")
        case_btn.setMinimumHeight(36)
        case_btn.clicked.connect(self.open_case_builder)
        layout.addWidget(case_btn)

        layout.addStretch()
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def _check_join_for_advanced(self) -> bool:
        """
        В режиме JOIN по ТЗ разрешены только сортировка и фильтрация.
        Все остальные функции (GROUP BY, подзапросы, CASE и т.п.) блокируем.
        Возвращает True, если функция недоступна из‑за JOIN.
        """
        if getattr(self.task_dialog, "is_join_mode", False):
            QMessageBox.information(
                self,
                "Недоступно",
                "Эта операция недоступна при активных соединениях (JOIN).\n"
                "В режиме JOIN разрешены только сортировка и фильтрация."
            )
            return True
        return False

    def open_sort(self):
        dlg = SortDialog(self.selected_column, self)
        if dlg.exec_():
            direction = dlg.direction
            if hasattr(self.task_dialog, "add_sort_clause"):
                self.task_dialog.add_sort_clause(self.selected_column, direction)

    def open_filter(self):
        dlg = FilterDialog(self.selected_column, self.prefill_value, self)
        if dlg.exec_():
            where_clause = dlg.where_clause
            if hasattr(self.task_dialog, "add_where_clause"):
                # сортировка/фильтрация разрешены в JOIN по ТЗ
                self.task_dialog.add_where_clause(where_clause)

    def open_group(self):
        # группировка уже была ограничена, но усиливаем логику под общее правило
        if self._check_join_for_advanced():
            return
        dlg = GroupDialog(self.selected_column, self.columns_info, self)
        if dlg.exec_():
            if dlg.group_by_selected and hasattr(self.task_dialog, "add_group_by_column"):
                self.task_dialog.add_group_by_column(dlg.group_by_column)
            if dlg.aggregate_expression and hasattr(self.task_dialog, "add_select_aggregate"):
                self.task_dialog.add_select_aggregate(dlg.aggregate_expression)
            if dlg.having_clause and hasattr(self.task_dialog, "add_having_clause"):
                self.task_dialog.add_having_clause(dlg.having_clause)

    def open_subquery_builder(self):
        # Подзапросы запрещаем при JOIN
        if self._check_join_for_advanced():
            return
        dlg = SubqueryDialog(self.controller, self.table_name, self)
        if dlg.exec_():
            clause = dlg.get_clause()
            if clause:
                # подзапросы добавляются как готовый фрагмент WHERE
                self.task_dialog.add_where_clause(clause)

    def open_case_builder(self):
        # CASE / COALESCE / NULLIF запрещаем при JOIN
        if self._check_join_for_advanced():
            return
        dlg = CaseExpressionDialog(self.controller, self.table_name, self)
        if dlg.exec_():
            expr = dlg.get_case_expression()
            if expr:
                self.task_dialog.add_select_expression(expr)
                self.task_dialog.refresh_with_current_clauses()


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


class FilterDialog(QDialog):
    """Диалог фильтрации WHERE для одного столбца."""
    def __init__(self, column, prefill_value="", parent=None):
        super().__init__(parent)
        self.column = column
        self.prefill_value = prefill_value
        self.where_clause = None

        self.setWindowTitle(f"Фильтрация (WHERE): {self.column}")
        self.setMinimumWidth(520)
        self.setup_ui()
        self.center_on_screen()

    def center_on_screen(self):
        screen = self.screen().geometry()
        self.move(screen.center() - self.rect().center())

    def setup_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.op_combo = QComboBox()
        self.op_combo.setMinimumWidth(150)
        self.op_combo.view().setMinimumWidth(180)
        self.op_combo.addItems(["=", "!=", "<", "<=", ">", ">=", "IN", "IS NULL", "IS NOT NULL"])
        form.addRow("Оператор:", self.op_combo)

        self.value_edit = QLineEdit()
        if self.prefill_value:
            self.value_edit.setText(self.prefill_value)
        form.addRow("Значение:", self.value_edit)

        layout.addLayout(form)

        self.op_combo.currentTextChanged.connect(self._toggle_value)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_dialog)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._toggle_value(self.op_combo.currentText())

    def _toggle_value(self, op):
        self.value_edit.setVisible(op not in ("IS NULL", "IS NOT NULL"))

    def accept_dialog(self):
        op = self.op_combo.currentText()
        if op in ("IS NULL", "IS NOT NULL"):
            self.where_clause = f"{self.column} {op}"
        else:
            val = self.value_edit.text().strip()
            if not val:
                QMessageBox.warning(self, "Ошибка", "Введите значение фильтра")
                return
            if op == "IN":
                parts = [p.strip() for p in val.split(",") if p.strip()]
                quoted = ", ".join([f"'{p}'" if not self._is_number(p) else p for p in parts])
                self.where_clause = f"{self.column} IN ({quoted})"
            else:
                value = val if self._is_number(val) else f"'{val}'"
                self.where_clause = f"{self.column} {op} {value}"
        self.accept()

    @staticmethod
    def _is_number(s):
        try:
            float(s)
            return True
        except ValueError:
            return False


class GroupDialog(QDialog):
    """Диалог группировки с выбором агрегатной функции и HAVING."""
    def __init__(self, column, columns_info, parent=None):
        super().__init__(parent)
        self.column = column
        self.columns_info = columns_info
        self.group_by_selected = True
        self.group_by_column = column
        self.aggregate_expression = None
        self.having_clause = None

        self.setWindowTitle(f"Группировка: {self.column}")
        self.setMinimumWidth(640)
        self.setup_ui()
        self.center_on_screen()

    def center_on_screen(self):
        screen = self.screen().geometry()
        self.move(screen.center() - self.rect().center())

    def setup_ui(self):
        layout = QVBoxLayout(self)
        checkbox_style = """
        QCheckBox { color: #333333; }
        QCheckBox::indicator {
            width: 14px; height: 14px;
            border: 1px solid #c0c0c0; border-radius: 3px; background: white;
        }
        QCheckBox::indicator:checked {
            background-color: #4a86e8; border: 1px solid #2a66c8;
        }
        """

        gb_group = QGroupBox("Группировка (GROUP BY)")
        gb_group.setStyleSheet("color: #333333;")
        gb_layout = QFormLayout(gb_group)

        self.gb_check = QCheckBox("Включить GROUP BY")
        self.gb_check.setChecked(True)
        self.gb_check.setStyleSheet(checkbox_style)
        gb_layout.addRow(self.gb_check)

        self.gb_col_combo = QComboBox()
        self.gb_col_combo.setMinimumWidth(200)
        self.gb_col_combo.view().setMinimumWidth(240)
        self.gb_col_combo.addItems([c['name'] for c in self.columns_info])
        self.gb_col_combo.setCurrentText(self.column)
        gb_layout.addRow("Столбец для группировки:", self.gb_col_combo)
        layout.addWidget(gb_group)

        agg_group = QGroupBox("Агрегатная функция")
        agg_group.setStyleSheet("color: #333333;")
        agg_form = QFormLayout(agg_group)

        self.agg_func = QComboBox()
        self.agg_func.setMinimumWidth(200)
        self.agg_func.view().setMinimumWidth(240)
        self.agg_func.addItems(["(нет)", "COUNT(*)", "COUNT", "SUM", "AVG", "MIN", "MAX"])
        agg_form.addRow("Функция:", self.agg_func)

        self.agg_target_combo = QComboBox()
        self.agg_target_combo.setMinimumWidth(200)
        self.agg_target_combo.view().setMinimumWidth(240)
        self.agg_target_combo.addItems([c['name'] for c in self.columns_info])
        self.agg_target_combo.setCurrentText(self.column)
        agg_form.addRow("Столбец для агрегата:", self.agg_target_combo)

        self.alias_edit = QLineEdit()
        agg_form.addRow("Псевдоним:", self.alias_edit)
        layout.addWidget(agg_group)

        having_group = QGroupBox("Фильтрация групп (HAVING)")
        having_group.setStyleSheet("color: #333333;")
        having_form = QFormLayout(having_group)

        self.having_enable = QCheckBox("Включить HAVING")
        self.having_enable.setChecked(False)
        self.having_enable.setStyleSheet(checkbox_style)
        having_form.addRow(self.having_enable)

        self.having_op = QComboBox()
        self.having_op.setMinimumWidth(140)
        self.having_op.view().setMinimumWidth(170)
        self.having_op.addItems(["=", "!=", "<", "<=", ">", ">="])
        having_form.addRow("Оператор:", self.having_op)

        self.having_value = QLineEdit()
        having_form.addRow("Значение:", self.having_value)
        layout.addWidget(having_group)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_dialog)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._toggle_agg_target()
        self.agg_func.currentTextChanged.connect(self._toggle_agg_target)
        self._toggle_having_ui()
        self.having_enable.stateChanged.connect(self._toggle_having_ui)

    def _toggle_agg_target(self):
        func = self.agg_func.currentText()
        self.agg_target_combo.setEnabled(func not in ("(нет)", "COUNT(*)"))

    def _toggle_having_ui(self):
        enabled = self.having_enable.isChecked()
        self.having_op.setEnabled(enabled)
        self.having_value.setEnabled(enabled)

    @staticmethod
    def _is_number(s):
        try:
            float(s)
            return True
        except ValueError:
            return False

    def _build_agg_expr(self):
        func_choice = self.agg_func.currentText()
        target_col = self.agg_target_combo.currentText()
        if func_choice == "(нет)":
            return None, None
        if func_choice == "COUNT(*)":
            base = "COUNT(*)"
        elif func_choice == "COUNT":
            base = f"COUNT({target_col})"
        else:
            base = f"{func_choice}({target_col})"
        alias = self.alias_edit.text().strip()
        expr = f"{base} AS {alias}" if alias else base
        return base, expr

    def accept_dialog(self):
        self.group_by_selected = self.gb_check.isChecked()
        self.group_by_column = self.gb_col_combo.currentText()
        base_func, expr = self._build_agg_expr()
        self.aggregate_expression = expr

        if self.having_enable.isChecked():
            if not base_func:
                QMessageBox.warning(self, "Ошибка", "Для HAVING выберите агрегатную функцию")
                return
            op = self.having_op.currentText()
            val_str = self.having_value.text().strip()
            if not val_str:
                QMessageBox.warning(self, "Ошибка", "Введите значение для HAVING")
                return
            value = val_str if self._is_number(val_str) else f"'{val_str}'"
            self.having_clause = f"{base_func} {op} {value}"
        else:
            self.having_clause = None

        self.accept()


class SubqueryDialog(QDialog):
    """Диалог подзапросов ANY/ALL/EXISTS."""
    def __init__(self, controller, outer_table, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.outer_table = outer_table
        self.setWindowTitle("Конструктор подзапроса")
        self.setMinimumWidth(620)
        self.clause = ""
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        mode_row = QFormLayout()
        self.mode_combo = QComboBox()
        self.mode_combo.setMinimumWidth(180)
        self.mode_combo.view().setMinimumWidth(210)
        self.mode_combo.addItems(["EXISTS", "ANY", "ALL"])
        mode_row.addRow("Оператор подзапроса:", self.mode_combo)
        layout.addLayout(mode_row)

        # Блок для ANY/ALL
        self.anyall_group = QGroupBox("Параметры для ANY/ALL")
        anyall_layout = QFormLayout(self.anyall_group)

        self.outer_col_combo = QComboBox()
        self.outer_col_combo.setMinimumWidth(180)
        self.outer_col_combo.view().setMinimumWidth(210)
        outer_cols = [c['name'] for c in self.controller.get_table_columns(self.outer_table)]
        self.outer_col_combo.addItems(outer_cols)
        anyall_layout.addRow("Внешний столбец:", self.outer_col_combo)

        self.comp_op_combo = QComboBox()
        self.comp_op_combo.setMinimumWidth(120)
        self.comp_op_combo.view().setMinimumWidth(150)
        self.comp_op_combo.addItems(["=", "!=", ">", "<", ">=", "<="])
        anyall_layout.addRow("Оператор сравнения:", self.comp_op_combo)
        layout.addWidget(self.anyall_group)

        self.sub_table_combo = QComboBox()
        self.sub_table_combo.setMinimumWidth(220)
        self.sub_table_combo.view().setMinimumWidth(260)
        all_tables = self.controller.get_all_tables()
        all_tables += ['actors', 'plots', 'performances', 'actor_performances', 'game_data']
        self.sub_table_combo.addItems(sorted(set(all_tables)))
        layout.addWidget(QLabel("Таблица подзапроса:"))
        layout.addWidget(self.sub_table_combo)

        self.sub_col_combo = QComboBox()
        self.sub_col_combo.setMinimumWidth(220)
        self.sub_col_combo.view().setMinimumWidth(260)
        layout.addWidget(QLabel("Столбец подзапроса для выборки (ANY/ALL):"))
        layout.addWidget(self.sub_col_combo)

        layout.addWidget(QLabel("Корреляция (внешний = внутренний):"))
        corr_layout = QHBoxLayout()
        self.where_outer_combo = QComboBox()
        self.where_outer_combo.setMinimumWidth(180)
        self.where_outer_combo.view().setMinimumWidth(210)
        self.where_sub_combo = QComboBox()
        self.where_sub_combo.setMinimumWidth(180)
        self.where_sub_combo.view().setMinimumWidth(210)
        corr_layout.addWidget(self.where_outer_combo)
        corr_layout.addWidget(QLabel("="))
        corr_layout.addWidget(self.where_sub_combo)
        layout.addLayout(corr_layout)

        self.filter_value_edit = QLineEdit()
        self.filter_value_edit.setPlaceholderText("Доп. значение для внутреннего WHERE (опционально)")
        layout.addWidget(self.filter_value_edit)

        self.mode_combo.currentTextChanged.connect(self._toggle_visibility)
        self.sub_table_combo.currentTextChanged.connect(self._reload_sub_columns)

        self._reload_sub_columns()
        self._toggle_visibility(self.mode_combo.currentText())

        btn_layout = QHBoxLayout()
        build_btn = QPushButton("Добавить условие")
        cancel_btn = QPushButton("Отмена")
        btn_layout.addWidget(build_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        build_btn.clicked.connect(self.build_clause)
        cancel_btn.clicked.connect(self.reject)

    def _reload_sub_columns(self):
        table = self.sub_table_combo.currentText()
        cols = [c['name'] for c in self.controller.get_table_columns(table)]
        self.sub_col_combo.clear()
        self.sub_col_combo.addItems(cols)
        self.where_outer_combo.clear()
        outer_cols = [c['name'] for c in self.controller.get_table_columns(self.outer_table)]
        self.where_outer_combo.addItems(outer_cols)
        self.where_sub_combo.clear()
        self.where_sub_combo.addItems(cols)

    def _toggle_visibility(self, mode):
        is_exists = (mode == "EXISTS")
        self.anyall_group.setEnabled(not is_exists)
        self.sub_col_combo.setEnabled(not is_exists)

    def _quote_if_needed(self, val: str) -> str:
        v = val.strip()
        if not v:
            return "''"
        try:
            float(v)
            return v
        except Exception:
            pass
        if (v.startswith("'") and v.endswith("'")) or (v.startswith('"') and v.endswith('"')):
            return v
        return f"'{v}'"

    def build_clause(self):
        mode = self.mode_combo.currentText()
        sub_table = self.sub_table_combo.currentText()
        sub_alias = "subq"
        sub_col = self.sub_col_combo.currentText()
        corr_outer = self.where_outer_combo.currentText()
        corr_inner = self.where_sub_combo.currentText()
        extra_val = self.filter_value_edit.text().strip()

        where_parts = [f"{sub_alias}.{corr_inner} = {self.outer_table}.{corr_outer}"]
        if extra_val:
            where_parts.append(f"{sub_alias}.{corr_inner} = {self._quote_if_needed(extra_val)}")
        where_clause = " AND ".join(where_parts)

        if mode == "EXISTS":
            self.clause = f"EXISTS (SELECT 1 FROM {sub_table} AS {sub_alias} WHERE {where_clause})"
        else:
            outer_col = self.outer_col_combo.currentText()
            comp = self.comp_op_combo.currentText()
            self.clause = (
                f"{self.outer_table}.{outer_col} {comp} {mode} "
                f"(SELECT {sub_alias}.{sub_col} FROM {sub_table} AS {sub_alias} WHERE {where_clause})"
            )
        self.accept()

    def get_clause(self):
        return self.clause


class CaseExpressionDialog(QDialog):
    """Конструктор CASE + COALESCE + NULLIF (CASE — необязателен)."""
    def __init__(self, controller, table_name, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.table_name = table_name
        self.setWindowTitle("Конструктор CASE / COALESCE / NULLIF")
        self.setMinimumWidth(700)
        self.when_rows = []
        self.case_alias_edit = None
        self.else_edit = None
        self.coalesce_value_edit = None
        self.nullif_first_edit = None
        self.nullif_second_edit = None
        self.case_group = None
        self.case_enable_check = None
        self.final_expr = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        self.case_enable_check = QCheckBox("Использовать CASE (WHEN ... THEN ...)")
        self.case_enable_check.setChecked(True)
        layout.addWidget(self.case_enable_check)

        self.case_group = QGroupBox("CASE выражение")
        case_layout = QVBoxLayout(self.case_group)

        case_layout.addWidget(QLabel("Условия WHEN ... THEN ..."))
        self.when_container = QVBoxLayout()
        case_layout.addLayout(self.when_container)

        add_when_btn = QPushButton("Добавить WHEN")
        add_when_btn.clicked.connect(self.add_when_row)
        case_layout.addWidget(add_when_btn)

        case_layout.addWidget(QLabel("Значение ELSE (опционально):"))
        self.else_edit = QLineEdit()
        case_layout.addWidget(self.else_edit)

        layout.addWidget(self.case_group)

        layout.addWidget(QLabel("Алиас (имя нового столбца):"))
        self.case_alias_edit = QLineEdit()
        layout.addWidget(self.case_alias_edit)

        layout.addWidget(QLabel("COALESCE значение (подставить вместо NULL, опционально):"))
        self.coalesce_value_edit = QLineEdit()
        layout.addWidget(self.coalesce_value_edit)

        layout.addWidget(QLabel("NULLIF (если expr1 == expr2 -> NULL, опционально):"))
        nullif_layout = QHBoxLayout()
        self.nullif_first_edit = QLineEdit()
        self.nullif_first_edit.setPlaceholderText("expr1 (обычно имя столбца)")
        self.nullif_second_edit = QLineEdit()
        self.nullif_second_edit.setPlaceholderText("expr2")
        nullif_layout.addWidget(self.nullif_first_edit)
        nullif_layout.addWidget(self.nullif_second_edit)
        layout.addLayout(nullif_layout)

        btn_layout = QHBoxLayout()
        build_btn = QPushButton("Добавить выражение")
        cancel_btn = QPushButton("Отмена")
        btn_layout.addWidget(build_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        build_btn.clicked.connect(self.build_expression)
        cancel_btn.clicked.connect(self.reject)

        self.case_enable_check.stateChanged.connect(self._toggle_case_block)

        self.add_when_row()

    def _toggle_case_block(self, state):
        enabled = state == Qt.Checked
        self.case_group.setEnabled(enabled)

    def add_when_row(self):
        row_layout = QHBoxLayout()
        cols_info = self.controller.get_table_columns(self.table_name)

        col_combo = QComboBox()
        col_combo.setMinimumWidth(150)
        col_combo.view().setMinimumWidth(180)
        col_combo.addItems([c['name'] for c in cols_info])

        op_combo = QComboBox()
        op_combo.setMinimumWidth(120)
        op_combo.view().setMinimumWidth(150)
        op_combo.addItems(["=", "!=", ">", "<", ">=", "<=", "IS NULL", "IS NOT NULL"])

        when_value_edit = QLineEdit()
        when_value_edit.setPlaceholderText("Значение для сравнения (кроме IS NULL)")

        then_value_edit = QLineEdit()
        then_value_edit.setPlaceholderText("THEN (результат)")

        row_layout.addWidget(col_combo)
        row_layout.addWidget(op_combo)
        row_layout.addWidget(when_value_edit)
        row_layout.addWidget(QLabel("THEN"))
        row_layout.addWidget(then_value_edit)

        self.when_container.addLayout(row_layout)
        self.when_rows.append((col_combo, op_combo, when_value_edit, then_value_edit))

    def _quote_if_needed(self, val: str):
        if val is None:
            return "NULL"
        val = val.strip()
        if val == "":
            return "''"
        try:
            float(val)
            return val
        except Exception:
            pass
        if (val.startswith("'") and val.endswith("'")) or (val.startswith('"') and val.endswith('"')):
            return val
        return f"'{val}'"

    def build_expression(self):
        use_case = self.case_enable_check.isChecked()
        expr = None
        has_when = False

        if use_case:
            parts = ["CASE"]
            for col_combo, op_combo, when_edit, then_edit in self.when_rows:
                col = col_combo.currentText()
                op = op_combo.currentText()
                when_raw = when_edit.text().strip()
                then_raw = then_edit.text().strip()

                if op in ("IS NULL", "IS NOT NULL"):
                    if not then_raw:
                        continue
                    parts.append(f"WHEN {self.table_name}.{col} {op} THEN {self._quote_if_needed(then_raw)}")
                    has_when = True
                else:
                    if not when_raw or not then_raw:
                        continue
                    q_when = self._quote_if_needed(when_raw)
                    parts.append(f"WHEN {self.table_name}.{col} {op} {q_when} THEN {self._quote_if_needed(then_raw)}")
                    has_when = True

            if not has_when:
                QMessageBox.warning(
                    self,
                    "Ошибка",
                    "Если CASE включён, необходимо добавить хотя бы одно корректное условие WHEN ... THEN ...\n"
                    "Либо отключите CASE (снимите галочку), чтобы использовать только COALESCE/NULLIF."
                )
                return

            else_val = self.else_edit.text().strip()
            if else_val:
                parts.append(f"ELSE {self._quote_if_needed(else_val)}")
            parts.append("END")
            expr = " ".join(parts)

        n1 = self.nullif_first_edit.text().strip()
        n2 = self.nullif_second_edit.text().strip()
        if n1 and n2:
            base = expr if expr else n1
            expr = f"NULLIF({base}, {self._quote_if_needed(n2)})"

        coalesce_val = self.coalesce_value_edit.text().strip()
        if coalesce_val:
            base = expr if expr else "NULL"
            expr = f"COALESCE({base}, {self._quote_if_needed(coalesce_val)})"

        if expr is None:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Ничего не задано: включите CASE или заполните поля COALESCE/NULLIF."
            )
            return

        alias = self.case_alias_edit.text().strip()
        if alias:
            expr = f"{expr} AS {alias}"

        self.final_expr = expr
        self.accept()

    def get_case_expression(self):
        return self.final_expr