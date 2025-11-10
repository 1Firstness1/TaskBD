"""
Модуль главного окна для приложения "Театральный менеджер".
Содержит основной класс MainWindow для управления интерфейсом программы.
"""
import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout,
                               QHBoxLayout, QWidget, QMessageBox, QTabWidget, QTextEdit)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from controller import TheaterController
from logger import Logger
from new_performance_d import NewPerformanceDialog
from performance_d import PerformanceHistoryDialog, PerformanceDetailsDialog
from plot_d import PlotManagementDialog
from actor_d import ActorsManagementDialog
from task_d import TaskDialog


class MainWindow(QMainWindow):
    """
    Главное окно приложения "Театральный менеджер".
    Содержит все основные функции управления театром.
    """

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.logger = Logger()

        self.setWindowTitle("Театральный менеджер")
        self.setMinimumSize(1100, 700)

        # Установка стилей для всего приложения
        self.set_application_style()

        # Инициализация интерфейса
        self.setup_ui()

        # Загрузка логов и обновление информации
        self.load_logs()
        self.update_game_info()

        self.logger.info("Главное окно инициализировано")

    def setup_ui(self):
        """Настройка пользовательского интерфейса главного окна."""
        # Создание центрального виджета
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        main_layout = QVBoxLayout(self.central_widget)

        # Заголовок
        title_label = QLabel("Театральный менеджер")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #2a66c8; margin: 10px;")
        main_layout.addWidget(title_label)

        # Информационная панель
        self.info_layout = QHBoxLayout()
        self.year_label = QLabel("Текущий год: ")
        self.capital_label = QLabel("Капитал: ")
        info_font = QFont()
        info_font.setPointSize(14)
        self.year_label.setFont(info_font)
        self.capital_label.setFont(info_font)
        self.info_layout.addWidget(self.year_label)
        self.info_layout.addStretch()
        self.info_layout.addWidget(self.capital_label)
        main_layout.addLayout(self.info_layout)

        # Панель кнопок
        self.setup_buttons(main_layout)

        # Инструкция по использованию
        instruction_text = """
        <h3>Инструкция по использованию:</h3>
        <p><b>1. Обновить данные</b> - обновляйте текущие данные в таблицах на стартовые</p>
        <p><b>2. Обновить схему</b> - обновляйте текущую схему в базе на новую</p>
        <p><b>3. Новая постановка</b> - организуйте спектакль, выбрав сюжет и актеров</p>
        <p><b>4. Постановки</b> - просмотрите результаты прошлых спектаклей</p>
        <p><b>5. Сюжеты</b> - добавляйте и удаляйте сюжеты</p>
        <p><b>6. Актёры</b> - добавляйте и удаляйте актеров</p>
        <p><b>7. Пропустить год</b> - продайте права на постановку и получите дополнительные средства</p>
        <p><b>8. ТЗ</b> - Техническое задание для выполнения контрольной</p>
        """
        instruction_label = QLabel(instruction_text)
        instruction_label.setWordWrap(True)
        instruction_label.setStyleSheet("background-color: #f0f0f0; padding: 15px; border-radius: 5px;")
        main_layout.addWidget(instruction_label)

        # Создание вкладок для логов и других данных
        self.data_tabs = QTabWidget()
        main_layout.addWidget(self.data_tabs)

        # Вкладка логов
        log_tab = QWidget()
        log_layout = QVBoxLayout(log_tab)
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setStyleSheet("background-color: white; color: black; ")
        log_layout.addWidget(self.log_display)
        self.data_tabs.addTab(log_tab, "Логи")
        self.data_tabs.setCurrentIndex(0)

        # Регистрация дисплея логов в логгере
        self.logger.set_main_window_log_display(self.log_display)

        # Кнопка отключения от БД
        disconnect_btn_layout = QHBoxLayout()
        self.disconnect_btn = QPushButton("Отключиться от БД")
        self.disconnect_btn.setFixedWidth(160)
        self.disconnect_btn.clicked.connect(self.disconnect_from_db)
        disconnect_btn_layout.addStretch()
        disconnect_btn_layout.addWidget(self.disconnect_btn)
        disconnect_btn_layout.addStretch()
        main_layout.addLayout(disconnect_btn_layout)

    def setup_buttons(self, main_layout):
        """Настройка панели кнопок главного окна."""
        buttons_layout = QHBoxLayout()

        # Кнопка обновления данных
        self.reset_db_btn = QPushButton("Обновить данные")
        self.reset_db_btn.clicked.connect(self.reset_database)
        buttons_layout.addWidget(self.reset_db_btn)

        # Кнопка обновления схемы
        self.reset_schema_btn = QPushButton("Обновить схему")
        self.reset_schema_btn.clicked.connect(self.reset_schema)
        buttons_layout.addWidget(self.reset_schema_btn)

        # Кнопка создания новой постановки
        self.new_show_btn = QPushButton("Новая постановка")
        self.new_show_btn.clicked.connect(self.open_new_show_dialog)
        buttons_layout.addWidget(self.new_show_btn)

        # Кнопка просмотра истории постановок
        self.history_btn = QPushButton("Постановки")
        self.history_btn.clicked.connect(self.show_history)
        buttons_layout.addWidget(self.history_btn)

        # Кнопка управления сюжетами
        self.plots_btn = QPushButton("Сюжеты")
        self.plots_btn.clicked.connect(self.manage_plots)
        buttons_layout.addWidget(self.plots_btn)

        # Кнопка управления актерами
        self.actors_btn = QPushButton("Актеры")
        self.actors_btn.clicked.connect(self.manage_actors)
        buttons_layout.addWidget(self.actors_btn)

        # Кнопка пропуска года
        self.skip_year_btn = QPushButton("Пропустить год")
        self.skip_year_btn.clicked.connect(self.skip_year)
        buttons_layout.addWidget(self.skip_year_btn)

        # Кнопка технического задания (управление БД)
        self.task_btn = QPushButton("ТЗ")
        self.task_btn.clicked.connect(self.open_task_dialog)
        buttons_layout.addWidget(self.task_btn)

        main_layout.addLayout(buttons_layout)

    def load_logs(self):
        """Загрузка содержимого лог-файла в окно логов."""
        try:
            with open("app.log", "r", encoding="utf-8") as f:
                log_content = f.read()
                self.log_display.setText(log_content)

            # Прокрутка к последней записи
            QTimer.singleShot(100, lambda: self.log_display.verticalScrollBar().setValue(
                self.log_display.verticalScrollBar().maximum()))
        except Exception as e:
            self.logger.error(f"Ошибка загрузки логов: {str(e)}")

    def append_log(self, message):
        """Добавление сообщения в окно логов с прокруткой вниз."""
        if hasattr(self, 'log_display') and self.log_display is not None:
            self.log_display.append(message)
            # Прокрутка вниз для отображения новых сообщений
            scrollbar = self.log_display.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def set_application_style(self):
        """Установка единого стиля для всего приложения."""
        app_style = """
        QMainWindow, QDialog {
            background-color: #f5f5f5;
        }
        QPushButton {
            background-color: #4a86e8;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #3a76d8;
        }
        QPushButton:pressed {
            background-color: #2a66c8;
        }
        QLabel {
            color: #333333;
        }
        QTableWidget {
            border: 1px solid #d0d0d0;
            gridline-color: #e0e0e0;
        }
        QTableWidget::item:selected {
            background-color: #d0e8ff;
        }
        QHeaderView::section {
            background-color: #e0e0e0;
            color: #333333;
            padding: 4px;
            border: 1px solid #c0c0c0;
            font-weight: bold;
        }
        QTabWidget::pane {
            border: 1px solid #c0c0c0;
            background-color: white;
        }
        QTabBar::tab {
            background-color: #e0e0e0;
            color: #333333;
            padding: 8px 12px;
            border: 1px solid #c0c0c0;
            border-bottom: none;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }
        QTabBar::tab:selected {
            background-color: white;
            font-weight: bold;
        }
        QComboBox {
            background-color: white;
            color: #333333;
            border: 1px solid #c0c0c0;
            border-radius: 4px;
            padding: 6px;
            min-height: 25px;
        }
        QComboBox::drop-down {
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 20px;
            border-left: 1px solid #c0c0c0;
            border-top-right-radius: 4px;
            border-bottom-right-radius: 4px;
        }
        QComboBox::down-arrow {
            image: none;
            width: 10px;
            height: 10px;
            background: #4a86e8;
            border-radius: 5px;
        }
        QComboBox QAbstractItemView {
            border: 1px solid #c0c0c0;
            border-radius: 4px;
            background-color: white;
            color: #333333;
            selection-background-color: #d0e8ff;
            selection-color: #333333;
            padding: 4px;
        }
        QLineEdit {
            background-color: white;
            color: #333333;
            border: 1px solid #c0c0c0;
            padding: 4px;
            min-width: 120px;
        }
        QTextEdit {
            border: 1px solid #c0c0c0;
            padding: 2px;
        }
        QSpinBox {
            background-color: white;
            color: #333333;
            border: 1px solid #c0c0c0;
            border-radius: 4px;
            padding: 1px 1px 1px 4px;
            min-width: 80px;
            max-height: 22px;
        }
        QSpinBox::up-button, QSpinBox::down-button {
            background-color: #e8e8e8;
            width: 16px;
            border: none;
            border-left: 1px solid #c0c0c0;
        }
        QSpinBox::up-button {
            border-top-right-radius: 3px;
            border-bottom: 1px solid #c0c0c0;
        }
        QSpinBox::down-button {
            border-bottom-right-radius: 3px;
        }
        QSpinBox::up-button:hover, QSpinBox::down-button:hover {
            background-color: #d0e8ff;
        }
        QSpinBox::up-button:pressed, QSpinBox::down-button:pressed {
            background-color: #4a86e8;
        }
        QSpinBox::up-arrow, QSpinBox::down-arrow {
            width: 6px;
            height: 6px;
            background: #4a86e8;
        }
        QSpinBox:focus {
            border: 1px solid #4a86e8;
        }
        """
        self.setStyleSheet(app_style)

    def update_game_info(self):
        """Обновление информации о текущем годе и капитале в интерфейсе."""
        try:
            game_data = self.controller.get_game_state()

            if game_data and 'current_year' in game_data and 'capital' in game_data:
                self.year_label.setText(f"Текущий год: {game_data['current_year']}")
                # Форматирование числа с разделителями тысяч
                self.capital_label.setText(f"Капитал: {game_data['capital']:,} ₽".replace(',', ' '))
            else:
                # Если данных нет, пробуем инициализировать их
                self.year_label.setText("Текущий год: -")
                self.capital_label.setText("Капитал: -")

        except Exception as e:
            self.logger.error(f"Ошибка при обновлении информации: {str(e)}")
            self.year_label.setText("Текущий год: -")
            self.capital_label.setText("Капитал: -")

    def reset_database(self):
        """Сброс данных базы данных к начальному состоянию."""
        # Запрос подтверждения
        confirm = QMessageBox.question(
            self,
            "Подтверждение",
            "Вы уверены, что хотите обновить все данные к начальному состоянию?",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm == QMessageBox.Yes:
            # Сброс базы данных
            result = self.controller.reset_database()
            if result:
                QMessageBox.information(self, "Успех", "Данные успешно обновлены.")
                self.update_game_info()
            else:
                QMessageBox.critical(self, "Ошибка",
                                     "Не удалось обновить данные. Проверьте логи для получения подробной информации.")

    def reset_schema(self):
        """Сброс схемы базы данных (удаление и пересоздание всех таблиц)."""
        # Запрос подтверждения
        confirm = QMessageBox.question(
            self,
            "Подтверждение",
            "Вы уверены, что хотите полностью обновить схему базы данных? Все данные будут удалены.",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm == QMessageBox.Yes:
            # Сброс схемы
            result = self.controller.reset_schema()
            if result:
                QMessageBox.information(self, "Успех", "Схема базы данных успешно обновлена.")
                self.update_game_info()
            else:
                QMessageBox.critical(self, "Ошибка",
                                     "Не удалось обновить схему базы данных. Проверьте логи для получения подробной информации.")

    def open_new_show_dialog(self):
        """Открытие диалога создания новой постановки."""
        try:
            dialog = NewPerformanceDialog(self.controller, self)
            if dialog.exec():
                self.update_game_info()
        except Exception as e:
            err_box = QMessageBox(self)
            err_box.setWindowTitle("Ошибка")
            err_box.setText(f"Не удалось получить данные о игровой сессии.")
            err_box.setIcon(QMessageBox.Critical)
            err_box.exec()

    def show_history(self):
        """Просмотр истории постановок."""
        history_dialog = PerformanceHistoryDialog(self.controller, self)
        history_dialog.exec()

    def show_performance_details(self, performance_id):
        """Просмотр детальной информации о постановке."""
        details = self.controller.get_performance_details(performance_id)

        if not details:
            QMessageBox.warning(self, "Ошибка", "Не удалось получить информацию о спектакле.")
            return

        performance = details['performance']
        actors = details['actors']

        dialog = PerformanceDetailsDialog(performance, actors, self)
        dialog.exec()

    def manage_plots(self):
        """Открытие диалога управления сюжетами."""
        dialog = PlotManagementDialog(self.controller, self)
        if dialog.exec():
            self.update_game_info()

    def manage_actors(self):
        """Открытие диалога управления актерами."""
        dialog = ActorsManagementDialog(self.controller, self)
        if dialog.exec():
            self.update_game_info()

    def open_task_dialog(self):
        """Открытие диалога технического задания (управление БД)."""
        dialog = TaskDialog(self.controller, self)
        dialog.exec()

    def skip_year(self):
        """Пропуск текущего года и получение дохода от продажи прав."""
        game_data = self.controller.get_game_state()

        if game_data and 'current_year' in game_data and 'capital' in game_data:
            # Запрос подтверждения
            result = QMessageBox.question(
                self,
                "Пропустить год",
                "Вы уверены, что хотите пропустить год? Театр продаст права на постановку другому театру и получит случайный доход.",
                QMessageBox.Yes | QMessageBox.No
            )

            if result == QMessageBox.Yes:
                # Пропуск года
                skip_result = self.controller.skip_year()
                # Отображение результата
                QMessageBox.information(
                    self,
                    "Год пропущен",
                    f"Вы пропустили год. Сейчас {skip_result['year']} год.\n\n"
                    f"Театр получил {skip_result['rights_sale']:,} ₽ за продажу прав на постановку.".replace(',',
                                                                                                             ' ')
                )
                self.update_game_info()
        else:
            err_box = QMessageBox(self)
            err_box.setWindowTitle("Ошибка")
            err_box.setText(f"Не удалось получить данные о игровой сессии.")
            err_box.setIcon(QMessageBox.Critical)
            err_box.exec()

    def disconnect_from_db(self):
        """Отключение от базы данных и выход из программы."""
        # Запрос подтверждения
        confirm = QMessageBox.question(
            self,
            "Подтверждение",
            "Вы уверены, что хотите отключиться от базы данных и выйти из программы?",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm == QMessageBox.Yes:
            self.logger.info("Отключение от базы данных и выход из программы")
            self.controller.close()
            self.close()

    def closeEvent(self, event):
        """Обработка события закрытия окна."""
        self.controller.close()
        event.accept()