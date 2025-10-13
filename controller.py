"""
Модуль управления театральными постановками.
Содержит основную бизнес-логику приложения.
"""
import random
import re
from data import DatabaseManager, ActorRank
from logger import Logger
# Добавляем импорты из Qt для работы с таблицами
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
        # Проверка достаточности капитала
        game_data = self.db.get_game_data()
        if game_data['capital'] < budget:
            return False, "Недостаточно средств в капитале"

        # Проверка сюжета и минимального бюджета
        plots = self.db.get_plots()
        plot = next((p for p in plots if p['plot_id'] == plot_id), None)

        if not plot:
            return False, "Сюжет не найден"

        if budget < plot['minimum_budget']:
            return False, "Бюджет меньше минимально необходимого для данного сюжета"

        # Создание спектакля в БД
        performance_id = self.db.create_performance(title, plot_id, year, budget)

        if performance_id:
            # Обновление капитала театра
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
        # Базовая стоимость контракта
        base_cost = 30000

        # Бонус за звание
        rank_order = ['Начинающий', 'Постоянный', 'Ведущий', 'Мастер', 'Заслуженный', 'Народный']
        rank_bonus = rank_order.index(actor['rank']) * 10000

        # Бонусы за опыт и награды
        experience_bonus = actor['experience'] * 2000
        awards_bonus = actor['awards_count'] * 5000

        # Расчет итоговой стоимости
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
        # Получение данных спектакля
        performances = self.db.get_performances()
        performance = next((p for p in performances if p['performance_id'] == performance_id), None)

        if not performance or performance['is_completed']:
            return False, "Спектакль не найден или уже завершен"

        # Получение данных сюжета
        plots = self.db.get_plots()
        plot = next((p for p in plots if p['plot_id'] == performance['plot_id']), None)

        # Получение списка актеров в спектакле
        actors = self.db.get_actors_in_performance(performance_id)

        # Расчет фактических затрат
        total_spent = plot['production_cost']
        for actor in actors:
            total_spent += actor['contract_cost']

        # Определение фактического бюджета и экономии
        actual_budget = min(performance['budget'], total_spent)
        saved_budget = performance['budget'] - actual_budget

        # Расчет базовой выручки (увеличена для лучшего баланса)
        base_revenue = actual_budget * (0.7 + 0.08 * plot['demand'])

        # Непредвиденные расходы (5-15% от бюджета)
        unexpected_expenses = int(actual_budget * random.uniform(0.05, 0.15))
        self.logger.info(f"Непредвиденные расходы спектакля {performance_id}: {unexpected_expenses}")

        # Проверка соответствия званий актеров требованиям ролей
        rank_order = ['Начинающий', 'Постоянный', 'Ведущий', 'Мастер', 'Заслуженный', 'Народный']
        actors_match_requirements = True

        # Предполагаем, что required_ranks содержит список минимальных званий для ролей
        required_ranks = plot.get('required_ranks', [])
        if isinstance(required_ranks, str) and required_ranks.startswith('{') and required_ranks.endswith('}'):
            required_ranks = required_ranks[1:-1].split(',')
            # Очистка кавычек
            required_ranks = [r.strip('"') for r in required_ranks]

        # Проверяем соответствие званий, если у нас есть требования
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

        # Расчет бонусов за актеров (улучшено для избежания больших убытков)
        actors_bonus = 0
        for actor in actors:
            rank_index = rank_order.index(actor['rank'])
            # Улучшенный множитель ранга для более справедливого расчета
            rank_multiplier = 1 + (rank_index * 0.15)

            award_bonus = actor['awards_count'] * 0.05
            exp_bonus = actor['experience'] * 0.01

            # Улучшенный расчет вклада актера
            actor_contribution = actor['contract_cost'] * rank_multiplier * (1 + award_bonus + exp_bonus)
            actors_bonus += actor_contribution

        # Определение типа спектакля с учетом соответствия требованиям
        fate_roll = random.random()

        # Корректировка шанса провала в зависимости от соответствия званий
        fail_chance = 0.4 if actors_match_requirements else 0.6

        # Провал: шанс зависит от соответствия званий
        if fate_roll < fail_chance:
            self.logger.info(f"Спектакль {performance_id} оказался провальным!")
            # При несоответствии званий - еще хуже результат
            random_factor = random.uniform(0.4, 0.7) if actors_match_requirements else random.uniform(0.3, 0.5)
        # Норма: ~30% шанс с доходом 70-100% от ожидаемого
        elif fate_roll < 0.9:
            self.logger.info(f"Спектакль {performance_id} прошел в обычном режиме")
            random_factor = random.uniform(0.7, 1.0)
        # Успех: 10% шанс с доходом 100-140% от ожидаемого (увеличен максимальный бонус)
        else:
            self.logger.info(f"Спектакль {performance_id} прошел с большим успехом!")
            random_factor = random.uniform(1.0, 1.4)

        # Итоговая выручка
        total_revenue = int((base_revenue + actors_bonus) * random_factor)

        # Учитываем непредвиденные расходы при расчете прибыли
        total_expenses = actual_budget + unexpected_expenses
        profit = total_revenue - total_expenses

        # Обновление данных в БД - передаем полные расходы включая непредвиденные
        self.db.update_performance_budget(performance_id, total_expenses)
        self.db.complete_performance(performance_id, total_revenue)

        # Обновление игровых данных - ИСПРАВЛЕННЫЙ РАСЧЕТ
        game_data = self.db.get_game_data()
        new_capital = game_data['capital'] + total_revenue + saved_budget - unexpected_expenses
        current_year = game_data['current_year'] + 1
        self.db.update_game_data(current_year, new_capital)

        # Определение успешных актеров для награждения (только если прибыль положительная)
        successful_actors = []
        if profit > 0:
            sorted_actors = sorted(actors,
                                   key=lambda a: (rank_order.index(a['rank']),
                                                  a['experience'],
                                                  a['awards_count']),
                                   reverse=True)

            # Награждение лучших актеров
            for i, actor in enumerate(sorted_actors[:3]):
                self.db.award_actor(actor['actor_id'])
                successful_actors.append(actor)

                # Повышение звания самого успешного актера
                if i == 0 and profit > total_expenses * 0.3:  # Снизили порог для повышения
                    self.db.upgrade_actor_rank(actor['actor_id'])

        # Формирование результатов
        return True, {
            'revenue': total_revenue,
            'budget': total_expenses,  # Включаем непредвиденные расходы в общий бюджет
            'original_budget': performance['budget'],
            'saved_budget': saved_budget,
            'profit': profit,
            'awarded_actors': successful_actors,
            'unexpected_expenses': unexpected_expenses  # Добавлено в результаты
        }

    def skip_year(self):
        """
        Пропуск текущего года с продажей прав на постановку.

        Returns:
            dict: Новый год, капитал и доход от продажи прав
        """
        # Получение текущих данных
        game_data = self.db.get_game_data()
        current_year = game_data['current_year']
        current_capital = game_data['capital']

        # Расчет дохода от продажи прав (10-20% от капитала)
        rights_sale = int(current_capital * random.uniform(0.1, 0.2))

        # Обновление данных
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


# Вспомогательные классы для таблиц

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
        # Сохраняем текущий текст и позицию курсора
        old_text = self.text()
        cursor_pos = self.cursorPosition()

        # Вызываем стандартную обработку нажатия клавиш
        super().keyPressEvent(event)

        # Проверяем валидность нового текста
        new_text = self.text()

        # Если текст пустой, разрешаем его
        if not new_text:
            return

        # Используем функцию валидации
        if self.controller.is_valid_text_input(new_text):
            return

        # Если текст не валиден, восстанавливаем старый текст
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
        # Сохраняем текущий текст и позицию курсора
        old_text = self.text()
        cursor_pos = self.cursorPosition()

        # Вызываем стандартную обработку нажатия клавиш
        super().keyPressEvent(event)

        # Проверяем валидность нового текста
        new_text = self.text()

        # Если текст пустой, разрешаем его
        if not new_text or self.controller.is_valid_text_input(new_text):
            return

        # Если текст не валиден, восстанавливаем старый текст
        self.setText(old_text)
        self.setCursorPosition(cursor_pos)