"""
Модуль управления театральными постановками.
Содержит основную бизнес-логику приложения.
"""
import random
import re
from data import DatabaseManager, ActorRank
from logger import Logger
from PySide6.QtWidgets import QTableWidgetItem, QLineEdit
from PySide6.QtCore import Qt


class TheaterController:
    """
    Основной контроллер театра, отвечающий за бизнес-логику приложения.
    Управляет актерами, постановками, бюджетом и результатами спектаклей.
    """
    def __init__(self):
        """Инициализация контроллера."""
        self.db = DatabaseManager()
        self.logger = Logger()
        self.is_connected = False

    def set_connection_params(self, dbname, user, password, host, port):
        """Установка параметров подключения к БД."""
        self.db.set_connection_params(dbname, user, password, host, port)

    def connect_to_database(self):
        """Установка соединения с БД."""
        self.is_connected = self.db.connect()
        return self.is_connected

    def create_database(self):
        """Создание новой базы данных."""
        return self.db.create_database()

    def initialize_database(self):
        """Инициализация схемы БД и заполнение тестовыми данными."""
        result1 = self.db.create_schema()
        result2 = self.db.init_sample_data()
        return result1 and result2

    def reset_database(self):
        """Сброс данных БД к начальному состоянию."""
        return self.db.reset_database()

    def reset_schema(self):
        """Сброс схемы БД и пересоздание всех таблиц."""
        return self.db.reset_schema()

    def get_game_state(self):
        """Получение текущего состояния игры (год, капитал)."""
        return self.db.get_game_data()

    def get_all_actors(self):
        """Получение списка всех актеров."""
        return self.db.get_actors()

    def get_all_plots(self):
        """Получение списка всех сюжетов."""
        return self.db.get_plots()

    def add_new_plot(self, title, minimum_budget, production_cost, roles_count, demand, required_ranks):
        """Добавление нового сюжета в базу данных."""
        return self.db.add_plot(title, minimum_budget, production_cost, roles_count, demand, required_ranks)

    def update_plot(self, plot_id, title, minimum_budget, production_cost, roles_count, demand, required_ranks):
        """Обновление данных сюжета."""
        return self.db.update_plot(plot_id, title, minimum_budget, production_cost, roles_count, demand, required_ranks)

    def delete_plot_by_id(self, plot_id):
        """Удаление сюжета по ID."""
        return self.db.delete_plot(plot_id)

    def get_performances_history(self):
        """Получение истории всех постановок."""
        return self.db.get_performances()

    def get_performance_details(self, performance_id):
        """
        Получение детальной информации о спектакле.

        Args:
            performance_id: ID спектакля

        Returns:
            dict: Информация о спектакле и задействованных актерах
        """
        performances = self.db.get_performances()
        performance = next((p for p in performances if p['performance_id'] == performance_id), None)

        if not performance:
            return None

        actors = self.db.get_actors_in_performance(performance_id)

        return {
            'performance': performance,
            'actors': actors
        }

    def create_new_performance(self, title, plot_id, year, budget):
        """
        Создание нового спектакля.

        Args:
            title: Название спектакля
            plot_id: ID сюжета
            year: Год постановки
            budget: Бюджет спектакля

        Returns:
            tuple: (успех операции (bool), ID спектакля или сообщение об ошибке)
        """
        game_data = self.db.get_game_data()
        if game_data['capital'] < budget:
            return False, "Недостаточно средств в капитале"

        plots = self.db.get_plots()
        plot = next((p for p in plots if p['plot_id'] == plot_id), None)

        if not plot:
            return False, "Сюжет не найден"

        if budget < plot['minimum_budget']:
            return False, "Бюджет меньше минимально необходимого для данного сюжета"

        performance_id = self.db.create_performance(title, plot_id, year, budget)

        if performance_id:
            new_capital = game_data['capital'] - budget
            self.db.update_game_data(year, new_capital)
            return True, performance_id
        else:
            return False, "Ошибка при создании спектакля"

    def assign_actor_to_performance(self, actor_id, performance_id, role, contract_cost):
        """Назначение актера на роль в спектакле."""
        return self.db.assign_actor_to_role(actor_id, performance_id, role, contract_cost)

    def calculate_contract_cost(self, actor):
        """
        Расчет стоимости контракта актера.

        Args:
            actor: Словарь с данными актера

        Returns:
            dict: Стоимость контракта, премии и общая сумма
        """
        base_cost = 30000

        rank_order = ['Начинающий', 'Постоянный', 'Ведущий', 'Мастер', 'Заслуженный', 'Народный']
        rank_bonus = rank_order.index(actor['rank']) * 10000

        experience_bonus = actor['experience'] * 2000
        awards_bonus = actor['awards_count'] * 5000

        contract_cost = base_cost + rank_bonus + experience_bonus + awards_bonus
        premium = contract_cost / 5

        return {
            'contract': contract_cost,
            'premium': premium,
            'total': contract_cost + premium
        }

    def calculate_performance_result(self, performance_id):
        """
        Расчет результатов спектакля.

        Args:
            performance_id: ID спектакля

        Returns:
            tuple: (успех операции (bool), результаты спектакля (dict))
        """
        performances = self.db.get_performances()
        performance = next((p for p in performances if p['performance_id'] == performance_id), None)

        if not performance or performance['is_completed']:
            return False, "Спектакль не найден или уже завершен"

        plots = self.db.get_plots()
        plot = next((p for p in plots if p['plot_id'] == performance['plot_id']), None)

        actors = self.db.get_actors_in_performance(performance_id)

        total_spent = plot['production_cost']
        for actor in actors:
            total_spent += actor['contract_cost']

        actual_budget = min(performance['budget'], total_spent)
        saved_budget = performance['budget'] - actual_budget

        base_revenue = actual_budget * (0.7 + 0.08 * plot['demand'])

        unexpected_expenses = int(actual_budget * random.uniform(0.05, 0.15))
        self.logger.info(f"Непредвиденные расходы спектакля {performance_id}: {unexpected_expenses}")

        rank_order = ['Начинающий', 'Постоянный', 'Ведущий', 'Мастер', 'Заслуженный', 'Народный']
        actors_match_requirements = True

        required_ranks = plot.get('required_ranks', [])
        if isinstance(required_ranks, str) and required_ranks.startswith('{') and required_ranks.endswith('}'):
            required_ranks = required_ranks[1:-1].split(',')
            required_ranks = [r.strip('"') for r in required_ranks]

        if required_ranks and len(required_ranks) > 0:
            for i, actor in enumerate(actors):
                if i < len(required_ranks):
                    required_rank = required_ranks[i]
                    if required_rank in rank_order:
                        actor_rank_index = rank_order.index(actor['rank'])
                        required_rank_index = rank_order.index(required_rank)
                        if actor_rank_index < required_rank_index:
                            actors_match_requirements = False
                            self.logger.info(
                                f"Актер {actor['last_name']} ({actor['rank']}) не соответствует требованию {required_rank}")
                            break

        actors_bonus = 0
        for actor in actors:
            rank_index = rank_order.index(actor['rank'])
            rank_multiplier = 1 + (rank_index * 0.15)

            award_bonus = actor['awards_count'] * 0.05
            exp_bonus = actor['experience'] * 0.01

            actor_contribution = actor['contract_cost'] * rank_multiplier * (1 + award_bonus + exp_bonus)
            actors_bonus += actor_contribution

        fate_roll = random.random()
        fail_chance = 0.4 if actors_match_requirements else 0.6

        if fate_roll < fail_chance:
            self.logger.info(f"Спектакль {performance_id} оказался провальным!")
            random_factor = random.uniform(0.4, 0.7) if actors_match_requirements else random.uniform(0.3, 0.5)
        elif fate_roll < 0.9:
            self.logger.info(f"Спектакль {performance_id} прошел в обычном режиме")
            random_factor = random.uniform(0.7, 1.0)
        else:
            self.logger.info(f"Спектакль {performance_id} прошел с большим успехом!")
            random_factor = random.uniform(1.0, 1.4)

        total_revenue = int((base_revenue + actors_bonus) * random_factor)

        total_expenses = actual_budget + unexpected_expenses
        profit = total_revenue - total_expenses

        self.db.update_performance_budget(performance_id, total_expenses)
        self.db.complete_performance(performance_id, total_revenue)

        game_data = self.db.get_game_data()
        new_capital = game_data['capital'] + total_revenue + saved_budget - unexpected_expenses
        current_year = game_data['current_year'] + 1
        self.db.update_game_data(current_year, new_capital)

        successful_actors = []
        if profit > 0:
            sorted_actors = sorted(actors,
                                   key=lambda a: (rank_order.index(a['rank']),
                                                  a['experience'],
                                                  a['awards_count']),
                                   reverse=True)

            for i, actor in enumerate(sorted_actors[:3]):
                self.db.award_actor(actor['actor_id'])
                successful_actors.append(actor)

                if i == 0 and profit > total_expenses * 0.3:
                    self.db.upgrade_actor_rank(actor['actor_id'])

        return True, {
            'revenue': total_revenue,
            'budget': total_expenses,
            'original_budget': performance['budget'],
            'saved_budget': saved_budget,
            'profit': profit,
            'awarded_actors': successful_actors,
            'unexpected_expenses': unexpected_expenses
        }

    def skip_year(self):
        """
        Пропуск текущего года с продажей прав на постановку.

        Returns:
            dict: Новый год, капитал и доход от продажи прав
        """
        game_data = self.db.get_game_data()
        current_year = game_data['current_year']
        current_capital = game_data['capital']

        rights_sale = int(current_capital * random.uniform(0.1, 0.2))

        new_capital = current_capital + rights_sale
        new_year = current_year + 1
        self.db.update_game_data(new_year, new_capital)

        return {
            'year': new_year,
            'capital': new_capital,
            'rights_sale': rights_sale
        }

    def add_new_actor(self, last_name, first_name, patronymic, rank, awards_count, experience):
        """Добавление нового актера в базу данных."""
        return self.db.add_actor(last_name, first_name, patronymic, rank, awards_count, experience)

    def update_actor(self, actor_id, last_name, first_name, patronymic, rank, awards_count, experience):
        """Обновление данных актера."""
        return self.db.update_actor(actor_id, last_name, first_name, patronymic, rank, awards_count, experience)

    def delete_actor_by_id(self, actor_id):
        """Удаление актера по его ID."""
        return self.db.delete_actor(actor_id)

    def is_valid_text_input(self, text):
        """
        Проверка валидности текстового ввода.
        Разрешены только буквы, цифры и пробелы.
        Максимальная длина - 100 символов.
        """
        return len(text) <= 100 and bool(re.match(r'^[а-яА-Яa-zA-Z0-9\s]+$', text))

    def close(self):
        """Закрытие соединения с БД."""
        self.db.disconnect()

    # ============ Методы для TaskDialog ============

    def get_all_tables(self):
        """Получение списка всех таблиц."""
        return self.db.get_all_table_names()

    def get_table_columns(self, table_name):
        """Получение информации о столбцах таблицы."""
        return self.db.get_table_columns(table_name)

    def get_table_data(self, table_name, columns=None, where=None, order_by=None, group_by=None, having=None, params=None):
        """Получение данных из таблицы с фильтрацией."""
        return self.db.get_table_data(table_name, columns, where, order_by, group_by, having, params)

    def add_column(self, table_name, column_name, data_type, nullable=True, default=None):
        """Добавление столбца в таблицу."""
        return self.db.add_table_column(table_name, column_name, data_type, nullable, default)

    def drop_column(self, table_name, column_name):
        """Удаление столбца из таблицы."""
        return self.db.drop_table_column(table_name, column_name)

    def rename_column(self, table_name, old_name, new_name):
        """Переименование столбца."""
        return self.db.rename_table_column(table_name, old_name, new_name)

    def rename_table(self, old_name, new_name):
        """Переименование таблицы."""
        return self.db.rename_table(old_name, new_name)

    def alter_column_type(self, table_name, column_name, new_type):
        """Изменение типа столбца."""
        return self.db.alter_column_type(table_name, column_name, new_type)

    def set_constraint(self, table_name, column_name, constraint_type, constraint_value=None):
        """Установка ограничения на столбец."""
        return self.db.set_column_constraint(table_name, column_name, constraint_type, constraint_value)

    def drop_constraint(self, table_name, column_name, constraint_type):
        """Снятие ограничения со столбца."""
        return self.db.drop_column_constraint(table_name, column_name, constraint_type)

    def insert_row(self, table_name, data):
        """Вставка новой записи."""
        return self.db.insert_table_row(table_name, data)

    def update_row(self, table_name, data, where_clause, where_params):
        """Обновление записи."""
        return self.db.update_table_row(table_name, data, where_clause, where_params)

    def delete_row(self, table_name, where_clause, where_params):
        """Удаление записи."""
        return self.db.delete_table_row(table_name, where_clause, where_params)

    def execute_join(self, tables_info, selected_columns, join_conditions, where=None, order_by=None, group_by=None,
                     having=None):
        """Выполнение JOIN запроса (поддержка WHERE/ORDER BY/GROUP BY/HAVING)."""
        return self.db.execute_join_query(tables_info, selected_columns, join_conditions, where, order_by, group_by,
                                          having)

    def execute_select(self, query, params=None):
        """Выполнение произвольного SELECT запроса."""
        return self.db.execute_select_query(query, params)

    def execute_update(self, query, params=None):
        """Выполнение произвольного UPDATE запроса."""
        return self.db.execute_update_query(query, params)

    def create_table(self, table_name, columns):
        """Создание новой таблицы."""
        return self.db.create_table(table_name, columns)

    def drop_table(self, table_name):
        """Удаление таблицы."""
        return self.db.drop_table(table_name)

    def list_enum_types(self):
        return self.db.list_enum_types()

    def list_composite_types(self):
        return self.db.list_composite_types()

    def create_enum_type(self, type_name, values):
        return self.db.create_enum_type(type_name, values)

    def create_composite_type(self, type_name, columns):
        return self.db.create_composite_type(type_name, columns)

    def drop_type(self, type_name):
        return self.db.drop_type(type_name)

    def list_enum_types(self):
        return self.db.list_enum_types()

    def list_enum_values(self, type_name):
        return self.db.list_enum_values(type_name)

    def create_enum_type(self, type_name, values):
        return self.db.create_enum_type(type_name, values)

    def add_enum_value(self, type_name, new_value, position=None, ref_value=None):
        return self.db.add_enum_value(type_name, new_value, position, ref_value)

    def rename_enum_value(self, type_name, old_value, new_value):
        return self.db.rename_enum_value(type_name, old_value, new_value)

    def drop_type(self, type_name):
        return self.db.drop_type(type_name)

    def list_composite_types(self):
        return self.db.list_composite_types()

    def list_composite_attributes(self, type_name):
        return self.db.list_composite_attributes(type_name)

    def create_composite_type(self, type_name, columns):
        return self.db.create_composite_type(type_name, columns)

    def composite_add_attribute(self, type_name, attr_name, data_type):
        return self.db.composite_add_attribute(type_name, attr_name, data_type)

    def composite_drop_attribute(self, type_name, attr_name):
        return self.db.composite_drop_attribute(type_name, attr_name)

    def composite_rename_attribute(self, type_name, old_name, new_name):
        return self.db.composite_rename_attribute(type_name, old_name, new_name)

    def composite_alter_attribute_type(self, type_name, attr_name, new_type):
        return self.db.composite_alter_attribute_type(type_name, attr_name, new_type)


class NumericTableItem(QTableWidgetItem):
    """
    Элемент таблицы для числовых значений с правильной сортировкой.
    """

    def __init__(self, text, value):
        super().__init__(text)
        self.value = value

    def __lt__(self, other):
        """Сравнение по числовому значению, а не по тексту."""
        if hasattr(other, 'value'):
            return self.value < other.value
        return super().__lt__(other)


class RankTableItem(QTableWidgetItem):
    """
    Элемент таблицы для званий актеров с правильной сортировкой.
    """

    def __init__(self, text):
        super().__init__(text)
        rank_order = ['Начинающий', 'Постоянный', 'Ведущий', 'Мастер', 'Заслуженный', 'Народный']
        self.rank_index = rank_order.index(text) if text in rank_order else -1

    def __lt__(self, other):
        """Сравнение по порядку званий, а не по алфавиту."""
        if isinstance(other, RankTableItem):
            return self.rank_index < other.rank_index
        return super().__lt__(other)


class CurrencyTableItem(QTableWidgetItem):
    """
    Элемент таблицы для денежных значений с правильной сортировкой.
    """

    def __init__(self, text, value):
        super().__init__(text)
        self.value = value

    def __lt__(self, other):
        """Сравнение по числовому значению, а не по тексту."""
        if hasattr(other, 'value'):
            return self.value < other.value
        return super().__lt__(other)


class DateTableItem(QTableWidgetItem):
    """
    Элемент таблицы для дат с правильной сортировкой.
    """

    def __init__(self, text, date_value):
        super().__init__(text)
        self.date_value = date_value

    def __lt__(self, other):
        """Сравнение по дате, а не по тексту."""
        if hasattr(other, 'date_value'):
            return self.date_value < other.date_value
        return super().__lt__(other)


class BooleanTableItem(QTableWidgetItem):
    """
    Элемент таблицы для булевых значений с правильной сортировкой.
    """

    def __init__(self, text, bool_value):
        super().__init__(text)
        self.bool_value = bool_value

    def __lt__(self, other):
        """Сравнение по булевому значению (False < True)."""
        if hasattr(other, 'bool_value'):
            return self.bool_value < other.bool_value
        return super().__lt__(other)


class TimestampTableItem(QTableWidgetItem):
    """
    Элемент таблицы для временных меток с правильной сортировкой.
    """

    def __init__(self, text, timestamp_value):
        super().__init__(text)
        self.timestamp_value = timestamp_value

    def __lt__(self, other):
        """Сравнение по временной метке, а не по тексту."""
        if hasattr(other, 'timestamp_value'):
            return self.timestamp_value < other.timestamp_value
        return super().__lt__(other)


class ValidatedLoginLineEdit(QLineEdit):
    """
    Поле ввода с валидацией для окна логина.
    Разрешает только определенные символы.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.controller = TheaterController()

    def keyPressEvent(self, event):
        """Обработка нажатия клавиш с валидацией."""
        old_text = self.text()
        cursor_pos = self.cursorPosition()

        super().keyPressEvent(event)

        new_text = self.text()

        if not new_text:
            return

        if self.controller.is_valid_text_input(new_text):
            return

        self.setText(old_text)
        self.setCursorPosition(cursor_pos)


class ValidatedLineEdit(QLineEdit):
    """
    Поле ввода с валидацией текста.
    Разрешает только определенные символы, заданные в контроллере.
    """

    def __init__(self, controller, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.controller = controller

    def keyPressEvent(self, event):
        """Обработка нажатия клавиш с валидацией."""
        old_text = self.text()
        cursor_pos = self.cursorPosition()

        super().keyPressEvent(event)

        new_text = self.text()

        if not new_text or self.controller.is_valid_text_input(new_text):
            return

        self.setText(old_text)
        self.setCursorPosition(cursor_pos)