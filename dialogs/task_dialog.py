from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QHeaderView, QMessageBox, QTabWidget, QTextEdit
)
from PySide6.QtCore import Qt
from controller import NumericTableItem, DateTableItem, BooleanTableItem, TimestampTableItem
from logger import Logger
import psycopg2

# Internal dialog imports
from .search_dialog import SearchDialog
from .edit_menu_dialog import EditMenuDialog
from .add_menu_dialog import AddMenuDialog
from .delete_menu_dialog import DeleteMenuDialog
from .type_management_dialog import TypeManagementDialog
from .display_options_dialog import DisplayOptionsDialog

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
        self.where_params = []         # список параметров для WHERE условий
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
        self.where_params = []
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
        cell_item = self.data_table.item(row, column)
        cell_value = cell_item.text() if cell_item else ""

        orig_column_name = column_name
        if self.is_join_mode and column_name in self.original_column_names:
            orig_column_name = self.original_column_names[column_name]

        from .column_actions_dialog import ColumnActionsDialog
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
            # Добавляем условие поиска в стек WHERE с параметрами
            if dialog.search_condition:
                self.add_where_clause(dialog.search_condition, getattr(dialog, 'search_params', None))

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
        # Параметры для WHERE (используются только если есть параметризованные условия)
        where_params = self.where_params if self.where_params else None

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
                params=None,  # JOIN режим не поддерживает параметры напрямую
                _select_override=(select_cols if select_cols else None)
            )
        else:
            self.load_table_data_filtered(
                columns=display_headers if display_headers else None,
                where=where,
                order_by=order_by,
                group_by=group_by,
                having=having,
                params=where_params,  # Используем сохраненные параметры
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
        Добавляет условие в стек WHERE. Если переданы params, они сохраняются
        для использования с параметризованными запросами (SIMILAR TO и т.д.).
        """
        if clause:
            self.where_clauses.append(clause)
            if params:
                # Параметры добавляются как список, который будет объединен при выполнении запроса
                if isinstance(params, list):
                    self.where_params.extend(params)
                else:
                    self.where_params.append(params)
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
            self.logger.info(f"Добавлено выражение в SELECT: {expression}")
            # Не вызываем refresh здесь, т.к. это делается в column_actions_dialog

    def _make_table_item(self, value):
        """
        Преобразование значения в QTableWidgetItem с адекватной обработкой NULL.
        """
        from datetime import datetime as _dt, date as _date

        if value is None:
            from PySide6.QtWidgets import QTableWidgetItem
            item = QTableWidgetItem("NULL")
            item.setForeground(Qt.gray)
            return item

        str_value = str(value)
        from PySide6.QtWidgets import QTableWidgetItem

        if isinstance(value, (int, float)):
            return NumericTableItem(str_value, value)
        elif isinstance(value, _date):
            return DateTableItem(str_value, value)
        elif isinstance(value, _dt):
            return TimestampTableItem(str_value, value)
        elif isinstance(value, bool):
            return BooleanTableItem(str_value, value)
        else:
            return QTableWidgetItem(str_value)

    def load_table_data_filtered(self, columns=None, where=None, order_by=None, group_by=None, having=None,
                                 params=None, _select_override=None):
        """Загрузка данных таблицы с учетом условий / группировок / вычисляемых столбцов."""
        if not self.current_table:
            return

        try:
            if self.is_join_mode:
                # JOIN режим
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

            else:
                # Обычный режим
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
            from PySide6.QtWidgets import QTableWidgetItem
            self.data_table.clearSpans()
            self.data_table.setRowCount(0)
            self.data_table.setColumnCount(len(self.current_columns))
            self.data_table.setHorizontalHeaderLabels(self.current_columns)
            self.data_table.setRowCount(len(data))

            for row_idx, row_data in enumerate(data):
                for col_idx, value in enumerate(row_data):
                    item = self._make_table_item(value)
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
            self.where_params = []
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
                        item = self._make_table_item(value)
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