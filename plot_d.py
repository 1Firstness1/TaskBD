"""
Модуль диалогов для управления сюжетами в приложении "Театральный менеджер".
"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFormLayout,
                               QPushButton, QComboBox, QSpinBox, QTableWidget,
                               QTableWidgetItem, QHeaderView, QMessageBox, QLineEdit)
from PySide6.QtCore import Qt

from controller import TheaterController, NumericTableItem, ValidatedLineEdit


class PlotManagementDialog(QDialog):
    """
    Диалог управления сюжетами.
    Позволяет просматривать, добавлять, редактировать и удалять сюжеты.
    """

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.all_plots = controller.get_all_plots()

        self.setWindowTitle("Сюжеты")
        self.setMinimumSize(800, 600)

        self.setup_ui()

    def setup_ui(self):
        """Настройка пользовательского интерфейса диалога."""
        layout = QVBoxLayout(self)

        # Заголовок
        title_label = QLabel("<h2>Сюжеты</h2>")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # Таблица сюжетов
        self.plots_table = QTableWidget()
        self.plots_table.setColumnCount(6)
        self.plots_table.setHorizontalHeaderLabels(
            ["ID", "Название", "Минимальный бюджет", "Стоимость постановки", "Количество ролей", "Спрос"])
        self.plots_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.plots_table.setEditTriggers(QTableWidget.NoEditTriggers)

        # Заполнение таблицы данными
        self.update_plots_table()

        # Включение сортировки и обработки двойного клика
        self.plots_table.setSortingEnabled(True)
        self.plots_table.cellDoubleClicked.connect(self.edit_plot)

        layout.addWidget(self.plots_table)

        # Кнопки действий
        buttons_layout = QHBoxLayout()

        add_plot_btn = QPushButton("Добавить сюжет")
        add_plot_btn.clicked.connect(self.add_plot)
        buttons_layout.addWidget(add_plot_btn)

        delete_plot_btn = QPushButton("Удалить сюжет")
        delete_plot_btn.clicked.connect(self.delete_plot)
        buttons_layout.addWidget(delete_plot_btn)

        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(close_btn)

        layout.addLayout(buttons_layout)

    def update_plots_table(self):
        """Обновление содержимого таблицы сюжетов."""
        # Получение актуального списка сюжетов
        self.all_plots = self.controller.get_all_plots()
        self.plots_table.setRowCount(len(self.all_plots))

        # Временно отключаем сортировку для заполнения таблицы
        self.plots_table.setSortingEnabled(False)

        # Заполнение таблицы данными
        for i, plot in enumerate(self.all_plots):
            id_item = NumericTableItem(str(plot['plot_id']), plot['plot_id'])
            title_item = QTableWidgetItem(plot['title'])
            min_budget_item = NumericTableItem(f"{plot['minimum_budget']:,} ₽".replace(',', ' '),
                                               plot['minimum_budget'])
            prod_cost_item = NumericTableItem(f"{plot['production_cost']:,} ₽".replace(',', ' '),
                                              plot['production_cost'])
            roles_count_item = NumericTableItem(str(plot['roles_count']), plot['roles_count'])
            demand_item = NumericTableItem(f"{plot['demand']}/10", plot['demand'])

            self.plots_table.setItem(i, 0, id_item)
            self.plots_table.setItem(i, 1, title_item)
            self.plots_table.setItem(i, 2, min_budget_item)
            self.plots_table.setItem(i, 3, prod_cost_item)
            self.plots_table.setItem(i, 4, roles_count_item)
            self.plots_table.setItem(i, 5, demand_item)

        # Включаем сортировку обратно
        self.plots_table.setSortingEnabled(True)

        # Устанавливаем сортировку по умолчанию по столбцу ID (столбец 0)
        self.plots_table.sortItems(0, Qt.AscendingOrder)

    def add_plot(self):
        """Открытие диалога добавления нового сюжета."""
        dialog = AddPlotDialog(self.controller, self)
        if dialog.exec():
            # Если диалог был принят, получаем данные и добавляем сюжет
            title = dialog.title_edit.text().strip()
            minimum_budget = dialog.min_budget_spin.value()
            production_cost = dialog.prod_cost_spin.value()
            roles_count = dialog.roles_count_spin.value()
            demand = dialog.demand_spin.value()

            # Получаем список требуемых званий
            required_ranks = []
            for i in range(roles_count):
                if i < len(dialog.rank_combos) and dialog.rank_combos[i].currentText():
                    required_ranks.append(dialog.rank_combos[i].currentText())
                else:
                    required_ranks.append("Начинающий")

            # Добавление сюжета в БД
            plot_id = self.controller.add_new_plot(title, minimum_budget, production_cost,
                                                   roles_count, demand, required_ranks)

            if plot_id:
                # Обновление таблицы при успешном добавлении
                self.update_plots_table()
                QMessageBox.information(self, "Успех", "Сюжет успешно добавлен.")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось добавить сюжет.")

    def edit_plot(self, row, column):
        """Открытие диалога редактирования сюжета."""
        # Получение ID сюжета из таблицы
        plot_id = int(self.plots_table.item(row, 0).text())
        plot = next((p for p in self.all_plots if p['plot_id'] == plot_id), None)

        if not plot:
            return

        # Открытие диалога редактирования
        dialog = EditPlotDialog(self.controller, plot, self)
        if dialog.exec():
            # Если диалог был принят, получаем данные и обновляем сюжет
            title = dialog.title_edit.text().strip()
            minimum_budget = dialog.min_budget_spin.value()
            production_cost = dialog.prod_cost_spin.value()
            roles_count = dialog.roles_count_spin.value()
            demand = dialog.demand_spin.value()

            # Получаем список требуемых званий
            required_ranks = []
            for i in range(roles_count):
                if i < len(dialog.rank_combos) and dialog.rank_combos[i].currentText():
                    required_ranks.append(dialog.rank_combos[i].currentText())
                else:
                    required_ranks.append("Начинающий")

            # Обновление сюжета в БД
            success, message = self.controller.update_plot(
                plot_id, title, minimum_budget, production_cost, roles_count, demand, required_ranks)

            if success:
                # Обновление таблицы при успешном обновлении
                self.update_plots_table()
                QMessageBox.information(self, "Успех", "Сюжет успешно обновлен.")
            else:
                QMessageBox.warning(self, "Ошибка", f"Не удалось обновить сюжет: {message}")

    def delete_plot(self):
        """Удаление выбранного сюжета."""
        # Проверка наличия выбранных строк
        selected_rows = self.plots_table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "Ошибка", "Выберите сюжет для удаления.")
            return

        # Получение ID сюжета
        row = selected_rows[0].row()
        plot_id = int(self.plots_table.item(row, 0).text())

        # Запрос подтверждения
        confirm = QMessageBox.question(
            self,
            "Подтверждение",
            "Вы уверены, что хотите удалить этот сюжет?",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm == QMessageBox.Yes:
            # Удаление сюжета из БД
            success, message = self.controller.delete_plot_by_id(plot_id)

            if success:
                # Обновление таблицы при успешном удалении
                self.update_plots_table()
                QMessageBox.information(self, "Успех", "Сюжет успешно удален.")
            else:
                QMessageBox.warning(self, "Ошибка", f"Не удалось удалить сюжет: {message}")


class AddPlotDialog(QDialog):
    """
    Диалог добавления нового сюжета.
    Позволяет ввести название, бюджет, количество ролей и т.д.
    """

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.setWindowTitle("Добавить сюжет")
        self.setMinimumWidth(500)

        self.rank_combos = []  # Список комбобоксов для выбора званий
        self.setup_ui()

    def setup_ui(self):
        """Настройка пользовательского интерфейса диалога."""
        main_layout = QVBoxLayout(self)

        # Форма для основных данных
        form_layout = QFormLayout()
        label_style = "color: #333333; font-weight: bold;"

        # Название сюжета
        title_label = QLabel("Название сюжета:")
        title_label.setStyleSheet(label_style)
        self.title_edit = ValidatedLineEdit(self.controller)
        form_layout.addRow(title_label, self.title_edit)

        # Минимальный бюджет
        min_budget_label = QLabel("Минимальный бюджет:")
        min_budget_label.setStyleSheet(label_style)
        self.min_budget_spin = QSpinBox()
        self.min_budget_spin.setRange(100000, 10000000)
        self.min_budget_spin.setSingleStep(50000)
        self.min_budget_spin.setValue(500000)
        self.min_budget_spin.setPrefix("₽ ")
        form_layout.addRow(min_budget_label, self.min_budget_spin)

        # Стоимость постановки
        prod_cost_label = QLabel("Стоимость постановки:")
        prod_cost_label.setStyleSheet(label_style)
        self.prod_cost_spin = QSpinBox()
        self.prod_cost_spin.setRange(50000, 5000000)
        self.prod_cost_spin.setSingleStep(50000)
        self.prod_cost_spin.setValue(300000)
        self.prod_cost_spin.setPrefix("₽ ")
        form_layout.addRow(prod_cost_label, self.prod_cost_spin)

        # Количество ролей
        roles_count_label = QLabel("Количество ролей:")
        roles_count_label.setStyleSheet(label_style)
        self.roles_count_spin = QSpinBox()
        self.roles_count_spin.setRange(1, 15)
        self.roles_count_spin.setValue(5)
        self.roles_count_spin.valueChanged.connect(self.update_role_ranks)
        form_layout.addRow(roles_count_label, self.roles_count_spin)

        # Спрос
        demand_label = QLabel("Спрос (1-10):")
        demand_label.setStyleSheet(label_style)
        self.demand_spin = QSpinBox()
        self.demand_spin.setRange(1, 10)
        self.demand_spin.setValue(5)
        form_layout.addRow(demand_label, self.demand_spin)

        main_layout.addLayout(form_layout)

        # Секция для выбора минимального звания для каждой роли
        self.ranks_title_label = QLabel("<h3>Минимальные звания для ролей</h3>")
        main_layout.addWidget(self.ranks_title_label)

        # Контейнер для званий ролей
        self.ranks_layout = QFormLayout()
        main_layout.addLayout(self.ranks_layout)

        # Инициализация выбора званий
        self.update_role_ranks(self.roles_count_spin.value())

        # Кнопки действий
        buttons_layout = QHBoxLayout()

        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self.validate_and_accept)
        buttons_layout.addWidget(save_btn)

        main_layout.addLayout(buttons_layout)

    def update_role_ranks(self, roles_count):
        """Обновление полей для выбора минимального звания для каждой роли."""
        # Очистка существующих полей
        for i in reversed(range(self.ranks_layout.rowCount())):
            self.ranks_layout.removeRow(i)

        self.rank_combos = []

        # Добавление комбобоксов для каждой роли
        rank_order = ['Начинающий', 'Постоянный', 'Ведущий', 'Мастер', 'Заслуженный', 'Народный']

        for i in range(roles_count):
            label = QLabel(f"Роль {i + 1}:")
            combo = QComboBox()

            for rank in rank_order:
                combo.addItem(rank)

            self.rank_combos.append(combo)
            self.ranks_layout.addRow(label, combo)

    def validate_and_accept(self):
        """Валидация введенных данных и закрытие диалога с принятием."""
        # Проверка заполнения обязательных полей
        if not self.title_edit.text().strip():
            QMessageBox.warning(self, "Ошибка", "Введите название сюжета")
            return

        # Проверка корректности бюджета
        if self.min_budget_spin.value() <= self.prod_cost_spin.value():
            QMessageBox.warning(self, "Ошибка", "Минимальный бюджет должен быть больше стоимости постановки")
            return

        # Если все проверки пройдены, принимаем диалог
        self.accept()


class EditPlotDialog(QDialog):
    """
    Диалог редактирования существующего сюжета.
    Позволяет изменить название, бюджет, количество ролей и т.д.
    """

    def __init__(self, controller, plot, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.plot = plot
        self.setWindowTitle(f"Редактировать сюжет: {plot['title']}")
        self.setMinimumWidth(500)

        self.rank_combos = []  # Список комбобоксов для выбора званий
        self.setup_ui()

    def setup_ui(self):
        """Настройка пользовательского интерфейса диалога."""
        main_layout = QVBoxLayout(self)

        # Форма для основных данных
        form_layout = QFormLayout()
        label_style = "color: #333333; font-weight: bold;"

        # Название сюжета
        title_label = QLabel("Название сюжета:")
        title_label.setStyleSheet(label_style)
        self.title_edit = ValidatedLineEdit(self.controller, self.plot['title'])
        form_layout.addRow(title_label, self.title_edit)

        # Минимальный бюджет
        min_budget_label = QLabel("Минимальный бюджет:")
        min_budget_label.setStyleSheet(label_style)
        self.min_budget_spin = QSpinBox()
        self.min_budget_spin.setRange(100000, 10000000)
        self.min_budget_spin.setSingleStep(50000)
        self.min_budget_spin.setValue(self.plot['minimum_budget'])
        self.min_budget_spin.setPrefix("₽ ")
        form_layout.addRow(min_budget_label, self.min_budget_spin)

        # Стоимость постановки
        prod_cost_label = QLabel("Стоимость постановки:")
        prod_cost_label.setStyleSheet(label_style)
        self.prod_cost_spin = QSpinBox()
        self.prod_cost_spin.setRange(50000, 5000000)
        self.prod_cost_spin.setSingleStep(50000)
        self.prod_cost_spin.setValue(self.plot['production_cost'])
        self.prod_cost_spin.setPrefix("₽ ")
        form_layout.addRow(prod_cost_label, self.prod_cost_spin)

        # Количество ролей
        roles_count_label = QLabel("Количество ролей:")
        roles_count_label.setStyleSheet(label_style)
        self.roles_count_spin = QSpinBox()
        self.roles_count_spin.setRange(1, 15)
        self.roles_count_spin.setValue(self.plot['roles_count'])
        self.roles_count_spin.valueChanged.connect(self.update_role_ranks)
        form_layout.addRow(roles_count_label, self.roles_count_spin)

        # Спрос
        demand_label = QLabel("Спрос (1-10):")
        demand_label.setStyleSheet(label_style)
        self.demand_spin = QSpinBox()
        self.demand_spin.setRange(1, 10)
        self.demand_spin.setValue(self.plot['demand'])
        form_layout.addRow(demand_label, self.demand_spin)

        main_layout.addLayout(form_layout)

        # Секция для выбора минимального звания для каждой роли
        self.ranks_title_label = QLabel("<h3>Минимальные звания для ролей</h3>")
        main_layout.addWidget(self.ranks_title_label)

        # Контейнер для званий ролей
        self.ranks_layout = QFormLayout()
        main_layout.addLayout(self.ranks_layout)

        # Инициализация выбора званий
        self.update_role_ranks(self.roles_count_spin.value())

        # Кнопки действий
        buttons_layout = QHBoxLayout()

        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self.validate_and_accept)
        buttons_layout.addWidget(save_btn)

        main_layout.addLayout(buttons_layout)

    def update_role_ranks(self, roles_count):
        """Обновление полей для выбора минимального звания для каждой роли."""
        # Очистка существующих полей
        for i in reversed(range(self.ranks_layout.rowCount())):
            self.ranks_layout.removeRow(i)

        self.rank_combos = []

        # Получаем текущие требуемые звания из сюжета
        required_ranks = self.plot.get('required_ranks', [])
        if isinstance(required_ranks, str) and required_ranks.startswith('{') and required_ranks.endswith('}'):
            required_ranks = required_ranks[1:-1].split(',')
            required_ranks = [r.strip('"') for r in required_ranks]
        elif not isinstance(required_ranks, list):
            required_ranks = ['Начинающий'] * roles_count

        # Добавление комбобоксов для каждой роли
        rank_order = ['Начинающий', 'Постоянный', 'Ведущий', 'Мастер', 'Заслуженный', 'Народный']

        for i in range(roles_count):
            label = QLabel(f"Роль {i + 1}:")
            combo = QComboBox()

            for rank in rank_order:
                combo.addItem(rank)

            # Устанавливаем текущее звание, если оно есть
            if i < len(required_ranks) and required_ranks[i] in rank_order:
                index = rank_order.index(required_ranks[i])
                combo.setCurrentIndex(index)

            self.rank_combos.append(combo)
            self.ranks_layout.addRow(label, combo)

    def validate_and_accept(self):
        """Валидация введенных данных и закрытие диалога с принятием."""
        # Проверка заполнения обязательных полей
        if not self.title_edit.text().strip():
            QMessageBox.warning(self, "Ошибка", "Введите название сюжета")
            return

        # Проверка корректности бюджета
        if self.min_budget_spin.value() <= self.prod_cost_spin.value():
            QMessageBox.warning(self, "Ошибка", "Минимальный бюджет должен быть больше стоимости постановки")
            return

        # Если все проверки пройдены, принимаем диалог
        self.accept()