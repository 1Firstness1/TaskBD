"""
Модуль диалога создания новой постановки для приложения "Театральный менеджер".
"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFormLayout,
                              QComboBox, QSpinBox, QPushButton, QScrollArea,
                              QFrame, QMessageBox, QLineEdit, QWidget)
from PySide6.QtCore import Qt

from controller import TheaterController, ValidatedLineEdit


class NewPerformanceDialog(QDialog):
    """
    Диалог создания новой постановки.
    Позволяет выбрать сюжет, установить бюджет и назначить актеров на роли.
    """

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.game_data = controller.get_game_state()
        self.all_plots = controller.get_all_plots()
        self.all_actors = controller.get_all_actors()

        self.setWindowTitle("Новая постановка")
        self.setMinimumSize(800, 600)

        self.setup_ui()

    def setup_ui(self):
        """Настройка пользовательского интерфейса диалога."""
        main_layout = QVBoxLayout(self)

        # Форма основных параметров спектакля
        form_layout = QFormLayout()

        # Название спектакля
        self.title_edit = ValidatedLineEdit(self.controller)
        form_layout.addRow("Название спектакля:", self.title_edit)

        # Выбор сюжета
        self.plot_combo = QComboBox()
        for plot in self.all_plots:
            self.plot_combo.addItem(f"{plot['title']} (мин. бюджет: {plot['minimum_budget']:,} ₽)".replace(',', ' '),
                                    plot['plot_id'])
        self.plot_combo.currentIndexChanged.connect(self.update_roles_section)
        form_layout.addRow("Сюжет:", self.plot_combo)

        # Информация о выбранном сюжете
        self.plot_info = QLabel()
        self.plot_info.setWordWrap(True)
        form_layout.addRow(self.plot_info)

        # Год постановки (текущий)
        self.year_label = QLabel(f"{self.game_data['current_year']}")
        form_layout.addRow("Год постановки:", self.year_label)

        # Бюджет спектакля
        self.budget_spin = QSpinBox()
        # Установка максимального значения равным капиталу театра
        self.budget_spin.setRange(100000, self.game_data['capital'])
        self.budget_spin.setSingleStep(50000)
        self.budget_spin.setValue(min(500000, self.game_data['capital']))  # Не превышаем капитал
        self.budget_spin.setPrefix("₽ ")
        self.budget_spin.valueChanged.connect(self.update_remaining_budget)
        form_layout.addRow("Бюджет спектакля:", self.budget_spin)

        # Доступный капитал
        self.capital_label = QLabel(f"{self.game_data['capital']:,} ₽".replace(',', ' '))
        form_layout.addRow("Доступный капитал:", self.capital_label)

        # Оставшийся бюджет
        self.remaining_budget_label = QLabel()
        form_layout.addRow("Оставшийся бюджет:", self.remaining_budget_label)

        main_layout.addLayout(form_layout)

        # Секция выбора актеров
        main_layout.addWidget(QLabel("<h3>Выбор актеров для ролей</h3>"))

        # Контейнер для ролей с прокруткой
        self.roles_widget = QWidget()
        self.roles_layout = QVBoxLayout(self.roles_widget)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.roles_widget)

        main_layout.addWidget(scroll_area)

        # Кнопки действий
        buttons_layout = QHBoxLayout()

        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(self.cancel_btn)

        self.create_btn = QPushButton("Создать постановку")
        self.create_btn.clicked.connect(self.create_performance)
        buttons_layout.addWidget(self.create_btn)

        main_layout.addLayout(buttons_layout)

        # Инициализация данных
        self.update_roles_section(0)
        self.update_remaining_budget()

    def calculate_contract_cost(self, actor):
        """Расчет стоимости контракта для актера."""
        return self.controller.calculate_contract_cost(actor)

    def update_roles_section(self, index):
        """Обновление секции с ролями в зависимости от выбранного сюжета."""
        if index < 0 or not self.all_plots:
            return

        # Получение данных выбранного сюжета
        plot_id = self.plot_combo.currentData()
        plot = next((p for p in self.all_plots if p['plot_id'] == plot_id), None)

        if not plot:
            return

        # Обновление информации о сюжете
        self.plot_info.setText(
            f"<b>Информация о сюжете:</b><br>"
            f"Минимальный бюджет: {plot['minimum_budget']:,} ₽<br>"
            f"Стоимость постановки: {plot['production_cost']:,} ₽<br>"
            f"Количество ролей: {plot['roles_count']}<br>"
            f"Спрос: {plot['demand']}/10"
        )
        self.plot_info.setStyleSheet("background-color: #f0f0f0; padding: 10px; border-radius: 5px;")

        # Установка минимального бюджета с учетом капитала
        min_budget = max(100000, plot['minimum_budget'])
        # Убедимся, что максимальный бюджет не превышает доступный капитал
        max_budget = self.game_data['capital']

        # Проверка, достаточно ли капитала для минимального бюджета
        if min_budget > max_budget:
            QMessageBox.warning(self, "Недостаточно средств",
                                f"Для постановки этого сюжета требуется минимум {min_budget:,} ₽, "
                                f"но доступный капитал составляет только {max_budget:,} ₽.")
            # Если недостаточно средств, можно выбрать другой сюжет или отменить
            self.budget_spin.setRange(min_budget, min_budget)  # Ограничиваем ввод
        else:
            self.budget_spin.setRange(min_budget, max_budget)

        # Если текущее значение за пределами диапазона, корректируем его
        current_value = self.budget_spin.value()
        if current_value < min_budget:
            self.budget_spin.setValue(min_budget)
        elif current_value > max_budget:
            self.budget_spin.setValue(max_budget)

        # Очистка предыдущих ролей
        for i in reversed(range(self.roles_layout.count())):
            widget = self.roles_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        # Порядок званий для сравнения
        rank_order = ['Начинающий', 'Постоянный', 'Ведущий', 'Мастер', 'Заслуженный', 'Народный']

        # Функция обновления списков актеров для всех ролей
        def update_actor_lists():
            # Сбор занятых актеров
            selected_actors = set()
            for i in range(self.roles_layout.count()):
                role_frame = self.roles_layout.itemAt(i).widget()
                if role_frame:
                    for child in role_frame.children():
                        if isinstance(child, QComboBox):
                            actor_id = child.currentData()
                            if actor_id:
                                selected_actors.add(actor_id)

            # Обновление списков актеров для каждой роли
            for i in range(self.roles_layout.count()):
                role_frame = self.roles_layout.itemAt(i).widget()
                if role_frame:
                    for child in role_frame.children():
                        if isinstance(child, QComboBox):
                            current_actor = child.currentData()
                            child.blockSignals(True)
                            current_index = child.currentIndex()
                            child.clear()
                            child.addItem("Выберите актера", None)

                            # Добавление актеров, которые не заняты или выбраны для текущей роли
                            for actor in self.all_actors:
                                if actor['actor_id'] == current_actor or actor['actor_id'] not in selected_actors:
                                    actor_name = f"{actor['last_name']} {actor['first_name']} {actor['patronymic']} ({actor['rank']})"
                                    child.addItem(actor_name, actor['actor_id'])

                                    # Выбор текущего актера, если он был выбран ранее
                                    if actor['actor_id'] == current_actor:
                                        child.setCurrentIndex(child.count() - 1)

                                    # Проверка требований к званию для роли
                                    required_ranks = plot['required_ranks'] if 'required_ranks' in plot else []
                                    role_index = self.roles_layout.indexOf(role_frame)

                                    # Получение минимального звания для текущей роли
                                    min_rank = None
                                    if role_index < len(required_ranks):
                                        if isinstance(required_ranks, str) and required_ranks.startswith(
                                                '{') and required_ranks.endswith('}'):
                                            required_ranks_list = required_ranks[1:-1].split(',')
                                            min_rank = required_ranks_list[role_index] if role_index < len(
                                                required_ranks_list) else None
                                        elif isinstance(required_ranks, list):
                                            min_rank = required_ranks[role_index]

                                        # Очистка кавычек, если они есть
                                        if min_rank and min_rank.startswith('"') and min_rank.endswith('"'):
                                            min_rank = min_rank[1:-1]

                                    # Предупреждение, если актер не соответствует требованиям
                                    if min_rank and min_rank in rank_order and actor['rank'] in rank_order:
                                        if rank_order.index(actor['rank']) < rank_order.index(min_rank):
                                            idx = child.count() - 1
                                            child.setItemData(idx, "Не соответствует требованиям звания",
                                                              Qt.ToolTipRole)

                            child.blockSignals(False)

            # Обновление оставшегося бюджета
            self.update_remaining_budget()

        # Создание полей для каждой роли
        for i in range(plot['roles_count']):
            role_frame = QFrame()
            role_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
            role_frame.setProperty("contract_cost", 0)
            role_layout = QHBoxLayout(role_frame)

            # Поле для названия роли
            role_name = ValidatedLineEdit(self.controller)
            role_name.setPlaceholderText(f"Роль {i + 1}")
            role_name.setMinimumWidth(180)
            role_name.setStyleSheet("color: black;")

            # Выпадающий список для выбора актера
            actor_combo = QComboBox()
            actor_combo.addItem("Выберите актера", None)

            # Функция для обработки выбора актера
            def create_actor_selected_handler(frame, label):
                def on_actor_selected(index):
                    combo = frame.findChild(QComboBox)
                    actor_id = combo.currentData()
                    if actor_id:
                        actor = next((a for a in self.all_actors if a['actor_id'] == actor_id), None)
                        if actor:
                            # Расчет стоимости контракта
                            costs = self.calculate_contract_cost(actor)
                            label.setText(
                                f"<b>Контракт:</b> {costs['contract']:,} ₽<br>"
                                f"<b>Премия:</b> {costs['premium']:,} ₽<br>"
                                f"<b>Итого:</b> {costs['total']:,} ₽".replace(',', ' ')
                            )
                            frame.setProperty("contract_cost", costs['total'])
                    else:
                        label.setText("<b>Контракт:</b> — ₽")
                        frame.setProperty("contract_cost", 0)

                    # Обновление списков актеров
                    update_actor_lists()

                return on_actor_selected

            # Метка для отображения стоимости контракта
            contract_label = QLabel("<b>Контракт:</b> — ₽")
            contract_label.setWordWrap(True)
            contract_label.setStyleSheet("color: white;")

            # Подключение обработчика выбора актера
            actor_combo.currentIndexChanged.connect(create_actor_selected_handler(role_frame, contract_label))

            # Метки для полей
            role_label = QLabel(f"Роль {i + 1}:")
            role_label.setStyleSheet("color: white;")
            actor_label = QLabel("Актер:")
            actor_label.setStyleSheet("color: white;")

            # Добавление полей в макет
            role_layout.addWidget(role_label)
            role_layout.addWidget(role_name, 2)
            role_layout.addWidget(actor_label)
            role_layout.addWidget(actor_combo, 3)
            role_layout.addWidget(contract_label, 2)

            # Добавление требований к званию, если они есть
            required_ranks = plot['required_ranks'] if 'required_ranks' in plot else []
            min_rank = None
            if i < len(required_ranks):
                if isinstance(required_ranks, str) and required_ranks.startswith('{') and required_ranks.endswith('}'):
                    required_ranks_list = required_ranks[1:-1].split(',')
                    min_rank = required_ranks_list[i] if i < len(required_ranks_list) else None
                elif isinstance(required_ranks, list):
                    min_rank = required_ranks[i]

                # Очистка кавычек, если они есть
                if min_rank and min_rank.startswith('"') and min_rank.endswith('"'):
                    min_rank = min_rank[1:-1]

            # Отображение минимального звания для роли
            if min_rank and min_rank in rank_order:
                rank_label = QLabel(f"Мин. звание: {min_rank}")
                rank_label.setStyleSheet("color: red; font-weight: bold;")
                role_layout.addWidget(rank_label)

            # Добавление рамки с полями роли в макет
            self.roles_layout.addWidget(role_frame)

        # Обновление списков актеров
        update_actor_lists()

    def update_remaining_budget(self):
        """Обновление отображения оставшегося бюджета."""
        # Общий бюджет
        total_budget = self.budget_spin.value()

        # Сумма контрактов
        contract_costs = 0
        for i in range(self.roles_layout.count()):
            role_frame = self.roles_layout.itemAt(i).widget()
            if role_frame:
                cost = role_frame.property("contract_cost")
                if cost:
                    contract_costs += cost

        # Добавление стоимости постановки
        plot_id = self.plot_combo.currentData()
        plot = next((p for p in self.all_plots if p['plot_id'] == plot_id), None)
        if plot:
            contract_costs += plot['production_cost']

        # Расчет оставшегося бюджета
        remaining = total_budget - contract_costs

        # Обновление метки с оставшимся бюджетом
        self.remaining_budget_label.setText(f"{int(remaining):,} ₽".replace(',', ' '))

        # Выделение красным, если бюджет превышен
        if remaining < 0:
            self.remaining_budget_label.setStyleSheet("color: red; font-weight: bold;")
        else:
            self.remaining_budget_label.setStyleSheet("")

    def create_performance(self):
        """Создание новой постановки с выбранными параметрами."""
        # Проверка названия спектакля
        if not self.title_edit.text().strip():
            QMessageBox.warning(self, "Ошибка", "Введите название спектакля")
            return

        # Получение данных выбранного сюжета
        plot_id = self.plot_combo.currentData()
        plot = next((p for p in self.all_plots if p['plot_id'] == plot_id), None)

        if not plot:
            QMessageBox.warning(self, "Ошибка", "Выберите сюжет")
            return

        # Проверка бюджета
        budget = self.budget_spin.value()
        if budget > self.game_data['capital']:
            QMessageBox.warning(self, "Ошибка", "Недостаточно средств в капитале")
            return

        if budget < plot['minimum_budget']:
            QMessageBox.warning(self, "Ошибка", f"Бюджет должен быть не менее {plot['minimum_budget']:,} ₽")
            return

        # Сбор данных о ролях и актерах
        roles_data = []
        assigned_actors = set()

        for i in range(self.roles_layout.count()):
            role_frame = self.roles_layout.itemAt(i).widget()
            if role_frame:
                role_name = None
                actor_id = None
                contract_cost = None

                # Получение данных из полей роли
                for child in role_frame.children():
                    if isinstance(child, QLineEdit):
                        role_name = child.text().strip()
                    elif isinstance(child, QComboBox):
                        actor_id = child.currentData()

                contract_cost = role_frame.property("contract_cost")

                # Проверки заполнения полей
                if not role_name:
                    QMessageBox.warning(self, "Ошибка", f"Введите название для роли {i + 1}")
                    return

                if not actor_id:
                    QMessageBox.warning(self, "Ошибка", f"Выберите актера для роли {i + 1}")
                    return

                # Проверка дублирования актеров
                if actor_id in assigned_actors:
                    QMessageBox.warning(self, "Ошибка", "Один актер не может играть несколько ролей")
                    return

                assigned_actors.add(actor_id)
                roles_data.append((role_name, actor_id, contract_cost))

        # Проверка количества ролей
        if len(roles_data) != plot['roles_count']:
            QMessageBox.warning(self, "Ошибка", f"Необходимо заполнить все {plot['roles_count']} ролей")
            return

        # Проверка превышения бюджета
        remaining_budget_text = self.remaining_budget_label.text().replace('₽', '').replace(' ', '').replace(',', '')
        try:
            remaining_budget = int(float(remaining_budget_text))
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Некорректное значение оставшегося бюджета")
            return

        if remaining_budget < 0:
            QMessageBox.warning(self, "Ошибка", "Превышен бюджет спектакля")
            return

        # Создание спектакля
        success, result = self.controller.create_new_performance(
            self.title_edit.text().strip(),
            plot_id,
            self.game_data['current_year'],
            budget
        )

        if not success:
            QMessageBox.warning(self, "Ошибка", f"Не удалось создать спектакль: {result}")
            return

        performance_id = result

        # Назначение актеров на роли
        for role_name, actor_id, contract_cost in roles_data:
            self.controller.assign_actor_to_performance(actor_id, performance_id, role_name, contract_cost)

        # Расчет результатов спектакля
        success, result = self.controller.calculate_performance_result(performance_id)

        if success:
            # Форматирование результатов
            profit = result['revenue'] - result['budget']
            profit_text = f"{profit:,} ₽".replace(',', ' ')
            profit_color = "green" if profit > 0 else "red"

            saved_budget_text = ""
            if result['saved_budget'] > 0:
                saved_budget_text = (
                    f"<p><b>Сэкономлено бюджета:</b> {result['saved_budget']:,} ₽ "
                    f"(возвращено в капитал)</p>".replace(',', ' ')
                )

            # Формирование текста результатов
            result_text = (
                f"<h2>Результаты спектакля '{self.title_edit.text()}'</h2>"
                f"<p><b>Изначальный бюджет:</b> {result['original_budget']:,} ₽</p>"
                f"<p><b>Фактический бюджет:</b> {result['budget']:,} ₽</p>"
                f"{saved_budget_text}"
                f"<p><b>Сборы:</b> {result['revenue']:,} ₽</p>"
                f"<p><b>Прибыль/Убыток:</b> <span style='color:{profit_color}'>{profit_text}</span></p>"
            )

            # Добавление информации о награжденных актерах
            if result['awarded_actors']:
                result_text += "<h3>Награжденные актеры:</h3><ul>"
                for actor in result['awarded_actors']:
                    result_text += f"<li>{actor['last_name']} {actor['first_name']} {actor['patronymic']}</li>"
                result_text += "</ul>"

            # Отображение результатов
            QMessageBox.information(self, "Результаты спектакля", result_text)
            self.accept()
        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось рассчитать результаты спектакля")