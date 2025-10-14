"""
Модуль диалогов, связанных с просмотром и деталями постановок для приложения "Театральный менеджер".
"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                              QTableWidget, QTableWidgetItem, QHeaderView)
from PySide6.QtCore import Qt

from controller import TheaterController, NumericTableItem, RankTableItem, CurrencyTableItem


class PerformanceDetailsDialog(QDialog):
    """
    Диалог для отображения подробной информации о спектакле.
    Показывает данные о спектакле и актерах, участвовавших в нем.
    """
    def __init__(self, performance, actors, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Детали спектакля '{performance['title']}'")
        self.setMinimumSize(600, 400)

        self.setup_ui(performance, actors)

    def setup_ui(self, performance, actors):
        """Настройка пользовательского интерфейса диалога."""
        layout = QVBoxLayout(self)

        # Информация о спектакле
        performance_info = QLabel(
            f"<h2>{performance['title']}</h2>"
            f"<p><b>Год:</b> {performance['year']}</p>"
            f"<p><b>Сюжет:</b> {performance['plot_title']}</p>"
            f"<p><b>Бюджет:</b> {performance['budget']:,} ₽</p>"
            f"<p><b>Сборы:</b> {performance['revenue']:,} ₽</p>"
        )
        performance_info.setWordWrap(True)
        layout.addWidget(performance_info)

        # Список актеров
        layout.addWidget(QLabel("<h3>Актеры в спектакле:</h3>"))

        # Таблица актеров
        actors_table = QTableWidget()
        actors_table.setColumnCount(6)
        actors_table.setHorizontalHeaderLabels(["ФИО", "Звание", "Опыт", "Награды", "Роль", "Гонорар"])
        actors_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        actors_table.setRowCount(len(actors))

        # Заполнение таблицы данными
        for i, actor in enumerate(actors):
            name_item = QTableWidgetItem(f"{actor['last_name']} {actor['first_name']} {actor['patronymic']}")
            rank_item = RankTableItem(actor['rank'])
            exp_item = NumericTableItem(str(actor['experience']), actor['experience'])
            awards_item = NumericTableItem(str(actor['awards_count']), actor['awards_count'])
            role_item = QTableWidgetItem(actor['role'])
            contract_item = CurrencyTableItem(f"{actor['contract_cost']:,} ₽".replace(',', ' '), actor['contract_cost'])

            actors_table.setItem(i, 0, name_item)
            actors_table.setItem(i, 1, rank_item)
            actors_table.setItem(i, 2, exp_item)
            actors_table.setItem(i, 3, awards_item)
            actors_table.setItem(i, 4, role_item)
            actors_table.setItem(i, 5, contract_item)

        # Настройка параметров таблицы
        actors_table.setEditTriggers(QTableWidget.NoEditTriggers)
        actors_table.setSortingEnabled(True)

        layout.addWidget(actors_table)

        # Кнопка закрытия
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


class PerformanceHistoryDialog(QDialog):
    """
    Диалог для просмотра истории постановок театра.
    Отображает список всех спектаклей с возможностью просмотра подробностей.
    """
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.parent_window = parent

        self.setWindowTitle("Постановки")
        self.setMinimumSize(800, 500)

        self.setup_ui()

    def setup_ui(self):
        """Настройка пользовательского интерфейса диалога."""
        layout = QVBoxLayout(self)

        # Заголовок
        title_label = QLabel("<h2>Постановки</h2>")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # Получение списка постановок
        self.performances = self.controller.get_performances_history()

        if not self.performances:
            # Если постановок нет, отображаем сообщение
            empty_label = QLabel("Постановок нет.")
            empty_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(empty_label)
        else:
            # Создание таблицы постановок
            self.history_table = QTableWidget()
            self.history_table.setColumnCount(6)
            self.history_table.setHorizontalHeaderLabels(
                ["Год", "Название", "Сюжет", "Бюджет", "Сборы", "Прибыль/Убыток"])
            self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            self.history_table.setRowCount(len(self.performances))

            # Словарь для связи строк таблицы с ID постановок
            self.row_to_performance_id = {}

            # Заполнение таблицы данными
            for i, perf in enumerate(self.performances):
                year_item = NumericTableItem(str(perf['year']), perf['year'])
                year_item.setData(Qt.UserRole, perf['performance_id'])

                title_item = QTableWidgetItem(perf['title'])
                plot_item = QTableWidgetItem(perf['plot_title'])
                budget_item = CurrencyTableItem(f"{perf['budget']:,} ₽".replace(',', ' '), perf['budget'])
                revenue_item = CurrencyTableItem(f"{perf['revenue']:,} ₽".replace(',', ' '), perf['revenue'])

                # Расчет прибыли/убытка
                profit = perf['revenue'] - perf['budget']
                profit_item = CurrencyTableItem(f"{profit:,} ₽".replace(',', ' '), profit)

                # Окрашивание прибыли/убытка в зависимости от результата
                if profit > 0:
                    profit_item.setForeground(Qt.green)
                elif profit < 0:
                    profit_item.setForeground(Qt.red)

                # Добавление элементов в таблицу
                self.history_table.setItem(i, 0, year_item)
                self.history_table.setItem(i, 1, title_item)
                self.history_table.setItem(i, 2, plot_item)
                self.history_table.setItem(i, 3, budget_item)
                self.history_table.setItem(i, 4, revenue_item)
                self.history_table.setItem(i, 5, profit_item)

                # Сохранение связи строки с ID постановки
                self.row_to_performance_id[i] = perf['performance_id']

            # Настройка параметров таблицы
            self.history_table.setSortingEnabled(True)
            self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
            self.history_table.cellDoubleClicked.connect(self.show_performance_details)

            layout.addWidget(self.history_table)

        # Кнопка закрытия
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def show_performance_details(self, row, col):
        """Открытие диалога с подробностями о выбранной постановке."""
        # Получение ID постановки из данных ячейки
        perf_id = self.history_table.item(row, 0).data(Qt.UserRole)
        # Отображение деталей постановки
        self.parent_window.show_performance_details(perf_id)