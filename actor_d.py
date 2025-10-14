"""
Модуль диалогов для управления актерами в приложении "Театральный менеджер".
"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFormLayout,
                              QPushButton, QComboBox, QSpinBox, QTableWidget,
                              QTableWidgetItem, QHeaderView, QMessageBox)
from PySide6.QtCore import Qt

from controller import TheaterController, NumericTableItem, RankTableItem, ValidatedLineEdit


class EditActorDialog(QDialog):
    """
    Диалог редактирования данных актера.
    Позволяет изменить ФИО, звание, количество наград и опыт.
    """
    def __init__(self, controller, actor, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.actor = actor

        self.setWindowTitle("Редактировать актера")
        self.setMinimumWidth(400)

        self.setup_ui()

    def setup_ui(self):
        """Настройка пользовательского интерфейса диалога."""
        layout = QFormLayout(self)

        # Стиль для меток
        label_style = "color: #333333; font-weight: bold;"

        # Поля для ввода данных актера
        # Фамилия
        last_name_label = QLabel("Фамилия:")
        last_name_label.setStyleSheet(label_style)
        self.last_name_edit = ValidatedLineEdit(self.controller, self.actor['last_name'])
        layout.addRow(last_name_label, self.last_name_edit)

        # Имя
        first_name_label = QLabel("Имя:")
        first_name_label.setStyleSheet(label_style)
        self.first_name_edit = ValidatedLineEdit(self.controller, self.actor['first_name'])
        layout.addRow(first_name_label, self.first_name_edit)

        # Отчество
        patronymic_label = QLabel("Отчество:")
        patronymic_label.setStyleSheet(label_style)
        self.patronymic_edit = ValidatedLineEdit(self.controller, self.actor['patronymic'])
        layout.addRow(patronymic_label, self.patronymic_edit)

        # Звание
        rank_label = QLabel("Звание:")
        rank_label.setStyleSheet(label_style)
        self.rank_combo = QComboBox()
        self.rank_combo.setMinimumWidth(145)
        rank_order = ['Начинающий', 'Постоянный', 'Ведущий', 'Мастер', 'Заслуженный', 'Народный']
        for rank in rank_order:
            self.rank_combo.addItem(rank)
        # Установка текущего звания
        index = self.rank_combo.findText(self.actor['rank'])
        if index >= 0:
            self.rank_combo.setCurrentIndex(index)
        layout.addRow(rank_label, self.rank_combo)

        # Количество наград
        awards_label = QLabel("Количество наград:")
        awards_label.setStyleSheet(label_style)
        self.awards_spin = QSpinBox()
        self.awards_spin.setRange(0, 65)
        self.awards_spin.setValue(self.actor['awards_count'])
        layout.addRow(awards_label, self.awards_spin)

        # Опыт работы
        exp_label = QLabel("Опыт (лет):")
        exp_label.setStyleSheet(label_style)
        self.exp_spin = QSpinBox()
        self.exp_spin.setRange(0, 65)
        self.exp_spin.setValue(self.actor['experience'])
        layout.addRow(exp_label, self.exp_spin)

        # Кнопки действий
        buttons_layout = QHBoxLayout()

        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self.validate_and_accept)
        buttons_layout.addWidget(save_btn)

        layout.addRow("", buttons_layout)

    def validate_and_accept(self):
        """Валидация введенных данных и закрытие диалога с принятием."""
        # Проверка заполнения обязательных полей
        if not self.last_name_edit.text().strip():
            QMessageBox.warning(self, "Ошибка", "Введите фамилию")
            return

        if not self.first_name_edit.text().strip():
            QMessageBox.warning(self, "Ошибка", "Введите имя")
            return

        # Если все проверки пройдены, принимаем диалог
        self.accept()


class ActorsManagementDialog(QDialog):
    """
    Диалог управления актерами.
    Позволяет просматривать, добавлять, редактировать и удалять актеров.
    """
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.all_actors = controller.get_all_actors()

        self.setWindowTitle("Актёры")
        self.setMinimumSize(800, 600)

        self.setup_ui()

    def setup_ui(self):
        """Настройка пользовательского интерфейса диалога."""
        layout = QVBoxLayout(self)

        # Заголовок
        title_label = QLabel("<h2>Актёры</h2>")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # Таблица актеров
        self.actors_table = QTableWidget()
        self.actors_table.setColumnCount(7)
        self.actors_table.setHorizontalHeaderLabels(
            ["ID", "Фамилия", "Имя", "Отчество", "Звание", "Опыт", "Награды"])
        self.actors_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.actors_table.setEditTriggers(QTableWidget.NoEditTriggers)

        # Заполнение таблицы данными
        self.update_actors_table()

        # Включение сортировки и обработки двойного клика
        self.actors_table.setSortingEnabled(True)
        self.actors_table.cellDoubleClicked.connect(self.edit_actor)

        layout.addWidget(self.actors_table)

        # Кнопки действий
        buttons_layout = QHBoxLayout()

        add_actor_btn = QPushButton("Добавить актера")
        add_actor_btn.clicked.connect(self.add_actor)
        buttons_layout.addWidget(add_actor_btn)

        delete_actor_btn = QPushButton("Удалить актера")
        delete_actor_btn.clicked.connect(self.delete_actor)
        buttons_layout.addWidget(delete_actor_btn)

        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(close_btn)

        layout.addLayout(buttons_layout)

    def update_actors_table(self):
        """Обновление содержимого таблицы актеров."""
        # Получение актуального списка актеров
        self.all_actors = self.controller.get_all_actors()
        self.actors_table.setRowCount(len(self.all_actors))

        # Временно отключаем сортировку для заполнения таблицы
        self.actors_table.setSortingEnabled(False)

        # Заполнение таблицы данными
        for i, actor in enumerate(self.all_actors):
            id_item = NumericTableItem(str(actor['actor_id']), actor['actor_id'])
            last_name_item = QTableWidgetItem(actor['last_name'])
            first_name_item = QTableWidgetItem(actor['first_name'])
            patronymic_item = QTableWidgetItem(actor['patronymic'])
            rank_item = RankTableItem(actor['rank'])
            exp_item = NumericTableItem(str(actor['experience']), actor['experience'])
            awards_item = NumericTableItem(str(actor['awards_count']), actor['awards_count'])

            self.actors_table.setItem(i, 0, id_item)
            self.actors_table.setItem(i, 1, last_name_item)
            self.actors_table.setItem(i, 2, first_name_item)
            self.actors_table.setItem(i, 3, patronymic_item)
            self.actors_table.setItem(i, 4, rank_item)
            self.actors_table.setItem(i, 5, exp_item)
            self.actors_table.setItem(i, 6, awards_item)

        # Включаем сортировку обратно
        self.actors_table.setSortingEnabled(True)

    def add_actor(self):
        """Открытие диалога добавления нового актера."""
        dialog = AddActorDialog(self.controller, self)
        if dialog.exec():
            # Если диалог был принят, получаем данные и добавляем актера
            last_name = dialog.last_name_edit.text().strip()
            first_name = dialog.first_name_edit.text().strip()
            patronymic = dialog.patronymic_edit.text().strip()
            rank = dialog.rank_combo.currentText()
            awards_count = dialog.awards_spin.value()
            experience = dialog.exp_spin.value()

            # Добавление актера в БД
            actor_id = self.controller.add_new_actor(last_name, first_name, patronymic, rank, awards_count, experience)

            if actor_id:
                # Обновление таблицы при успешном добавлении
                self.update_actors_table()
                QMessageBox.information(self, "Успех", "Актер успешно добавлен.")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось добавить актера.")

    def edit_actor(self, row, column):
        """Открытие диалога редактирования актера."""
        # Получение ID актера из таблицы
        actor_id = int(self.actors_table.item(row, 0).text())
        actor = next((a for a in self.all_actors if a['actor_id'] == actor_id), None)

        if not actor:
            return

        # Открытие диалога редактирования
        dialog = EditActorDialog(self.controller, actor, self)
        if dialog.exec():
            # Если диалог был принят, получаем данные и обновляем актера
            last_name = dialog.last_name_edit.text().strip()
            first_name = dialog.first_name_edit.text().strip()
            patronymic = dialog.patronymic_edit.text().strip()
            rank = dialog.rank_combo.currentText()
            awards_count = dialog.awards_spin.value()
            experience = dialog.exp_spin.value()

            # Обновление актера в БД
            success, message = self.controller.update_actor(
                actor_id, last_name, first_name, patronymic, rank, awards_count, experience)

            if success:
                # Обновление таблицы при успешном обновлении
                self.update_actors_table()
                QMessageBox.information(self, "Успех", "Актер успешно обновлен.")
            else:
                QMessageBox.warning(self, "Ошибка", f"Не удалось обновить актера: {message}")

    def delete_actor(self):
        """Удаление выбранного актера."""
        # Проверка наличия выбранных строк
        selected_rows = self.actors_table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "Ошибка", "Выберите актера для удаления.")
            return

        # Получение ID актера
        row = selected_rows[0].row()
        actor_id = int(self.actors_table.item(row, 0).text())

        # Запрос подтверждения
        confirm = QMessageBox.question(
            self,
            "Подтверждение",
            "Вы уверены, что хотите удалить этого актера?",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm == QMessageBox.Yes:
            # Удаление актера из БД
            success, message = self.controller.delete_actor_by_id(actor_id)

            if success:
                # Обновление таблицы при успешном удалении
                self.update_actors_table()
                QMessageBox.information(self, "Успех", "Актер успешно удален.")
            else:
                QMessageBox.warning(self, "Ошибка", f"Не удалось удалить актера: {message}")


class AddActorDialog(QDialog):
    """
    Диалог добавления нового актера.
    Позволяет ввести ФИО, звание, количество наград и опыт.
    """
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.setWindowTitle("Добавить актера")
        self.setMinimumWidth(400)

        self.setup_ui()

    def setup_ui(self):
        """Настройка пользовательского интерфейса диалога."""
        layout = QFormLayout(self)

        # Стиль для меток
        label_style = "color: #333333; font-weight: bold;"

        # Поля для ввода данных актера
        # Фамилия
        last_name_label = QLabel("Фамилия:")
        last_name_label.setStyleSheet(label_style)
        self.last_name_edit = ValidatedLineEdit(self.controller)
        layout.addRow(last_name_label, self.last_name_edit)

        # Имя
        first_name_label = QLabel("Имя:")
        first_name_label.setStyleSheet(label_style)
        self.first_name_edit = ValidatedLineEdit(self.controller)
        layout.addRow(first_name_label, self.first_name_edit)

        # Отчество
        patronymic_label = QLabel("Отчество:")
        patronymic_label.setStyleSheet(label_style)
        self.patronymic_edit = ValidatedLineEdit(self.controller)
        layout.addRow(patronymic_label, self.patronymic_edit)

        # Звание
        rank_label = QLabel("Звание:")
        rank_label.setStyleSheet(label_style)
        self.rank_combo = QComboBox()
        rank_order = ['Начинающий', 'Постоянный', 'Ведущий', 'Мастер', 'Заслуженный', 'Народный']
        for rank in rank_order:
            self.rank_combo.addItem(rank)
        layout.addRow(rank_label, self.rank_combo)

        # Количество наград
        awards_label = QLabel("Количество наград:")
        awards_label.setStyleSheet(label_style)
        self.awards_spin = QSpinBox()
        self.awards_spin.setRange(0, 20)
        layout.addRow(awards_label, self.awards_spin)

        # Опыт работы
        exp_label = QLabel("Опыт (лет):")
        exp_label.setStyleSheet(label_style)
        self.exp_spin = QSpinBox()
        self.exp_spin.setRange(0, 50)
        layout.addRow(exp_label, self.exp_spin)

        # Кнопки действий
        buttons_layout = QHBoxLayout()

        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self.validate_and_accept)
        buttons_layout.addWidget(save_btn)

        layout.addRow("", buttons_layout)

    def validate_and_accept(self):
        """Валидация введенных данных и закрытие диалога с принятием."""
        # Проверка заполнения обязательных полей
        if not self.last_name_edit.text().strip():
            QMessageBox.warning(self, "Ошибка", "Введите фамилию")
            return

        if not self.first_name_edit.text().strip():
            QMessageBox.warning(self, "Ошибка", "Введите имя")
            return

        # Если все проверки пройдены, принимаем диалог
        self.accept()