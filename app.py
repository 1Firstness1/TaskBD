"""
Модуль пользовательского интерфейса для приложения "Театральный менеджер".
Содержит классы для всех окон и диалогов приложения.
"""
import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout,
                              QHBoxLayout, QWidget, QDialog, QMessageBox, QComboBox,
                              QSpinBox, QTableWidget, QTableWidgetItem, QLineEdit,
                              QFormLayout, QTabWidget, QScrollArea, QFrame, QHeaderView, QTextEdit)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QIntValidator

from controller import TheaterController, NumericTableItem, RankTableItem, CurrencyTableItem, ValidatedLineEdit
from logger import Logger


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


class LoginDialog(QDialog):
    """
    Диалог авторизации и подключения к базе данных.
    Позволяет ввести параметры подключения, создать БД или подключиться к существующей.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.controller = TheaterController()
        self.logger = Logger()

        # Единый стиль для всех диалоговых окон сообщений
        self.message_box_style = """
            QMessageBox {
                background-color: #f5f5f5;
            }
            QMessageBox QLabel {
                color: #333333;
            }
            QMessageBox QPushButton {
                background-color: #4a86e8;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-weight: bold;
                min-width: 40px;
                min-height: 20px;
            }
            QMessageBox QPushButton:hover {
                background-color: #3a76d8;
            }
            QMessageBox QPushButton:pressed {
                background-color: #2a66c8;
            }
        """

        self.setup_ui()

    def setup_ui(self):
        """Настройка пользовательского интерфейса диалога."""
        self.setWindowTitle("Подключение к базе данных")
        self.setMinimumWidth(400)
        self.setModal(True)
        self.setStyleSheet("background-color: #f5f5f5;")

        layout = QVBoxLayout(self)

        # Заголовок
        title_label = QLabel("Театральный менеджер")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #2a66c8; ")
        layout.addWidget(title_label)

        # Форма для ввода параметров
        form_layout = QFormLayout()
        form_label_style = "color: #333333; font-weight: bold;"

        # Выбор базы данных
        self.db_combo = QComboBox()
        self.db_combo.addItem("taskBD")
        self.db_combo.addItem("postgres")
        self.db_combo.setStyleSheet("""
            QComboBox {
                background-color: white;
                color: black;
                border: 1px solid #c0c0c0;
                border-radius: 4px;
                padding: 6px;
                min-height: 5px;
                min-width: 88px;
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
                color: black;
                selection-background-color: #d0e8ff;
                selection-color: black;
                padding: 4px;
            }
        """)
        db_label = QLabel("База данных:")
        db_label.setStyleSheet(form_label_style)
        form_layout.addRow(db_label, self.db_combo)

        # Поле для ввода хоста
        self.host_edit = ValidatedLoginLineEdit("localhost")
        self.host_edit.setStyleSheet("color: black;")
        host_label = QLabel("Хост:")
        host_label.setStyleSheet(form_label_style)
        form_layout.addRow(host_label, self.host_edit)

        # Поле для ввода порта
        self.port_edit = ValidatedLoginLineEdit("5432")
        self.port_edit.setStyleSheet("color: black;")
        self.port_edit.setValidator(QIntValidator(1, 65535))
        port_label = QLabel("Порт:")
        port_label.setStyleSheet(form_label_style)
        form_layout.addRow(port_label, self.port_edit)

        # Поле для ввода имени пользователя
        self.user_edit = ValidatedLoginLineEdit("artem")
        self.user_edit.setStyleSheet("color: black;")
        user_label = QLabel("Пользователь:")
        user_label.setStyleSheet(form_label_style)
        form_layout.addRow(user_label, self.user_edit)

        # Поле для ввода пароля
        self.password_edit = QLineEdit("postgres")
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setStyleSheet("color: black;")
        password_label = QLabel("Пароль:")
        password_label.setStyleSheet(form_label_style)
        form_layout.addRow(password_label, self.password_edit)

        layout.addLayout(form_layout)

        # Кнопки действий
        buttons_layout = QHBoxLayout()

        button_style = """
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
        """

        # Кнопка подключения
        self.connect_btn = QPushButton("Подключиться")
        self.connect_btn.clicked.connect(self.try_connect)
        self.connect_btn.setStyleSheet(button_style)
        buttons_layout.addWidget(self.connect_btn)

        # Кнопка создания БД
        self.create_db_btn = QPushButton("Создать БД")
        self.create_db_btn.clicked.connect(self.create_database)
        self.create_db_btn.setStyleSheet(button_style)
        buttons_layout.addWidget(self.create_db_btn)

        # Кнопка выхода
        self.exit_btn = QPushButton("Выход")
        self.exit_btn.clicked.connect(self.reject)
        self.exit_btn.setStyleSheet(button_style)
        buttons_layout.addWidget(self.exit_btn)

        layout.addLayout(buttons_layout)

    def try_connect(self):
        """Попытка подключения к базе данных с введенными параметрами."""
        # Получение параметров из полей ввода
        dbname = self.db_combo.currentText()
        host = self.host_edit.text()
        port = self.port_edit.text()
        user = self.user_edit.text()
        password = self.password_edit.text()

        # Проверка заполнения всех обязательных полей
        if not dbname or not host or not port or not user:
            warn_box = QMessageBox(self)
            warn_box.setWindowTitle("Ошибка")
            warn_box.setText("Все поля, кроме пароля, должны быть заполнены")
            warn_box.setIcon(QMessageBox.Warning)
            warn_box.setStyleSheet(self.message_box_style)
            warn_box.exec()
            return

        # Установка параметров подключения
        self.controller.set_connection_params(dbname, user, password, host, port)

        # Попытка подключения
        if self.controller.connect_to_database():
            try:
                # Проверка существования структуры базы данных
                self.controller.db.cursor.execute(
                    "SELECT 1 FROM information_schema.tables WHERE table_name = 'game_data'")
                table_exists = self.controller.db.cursor.fetchone() is not None

                # Если структура не существует, предлагаем создать
                if not table_exists:
                    reply_box = QMessageBox(self)
                    reply_box.setWindowTitle("Схема не найдена")
                    reply_box.setText("Структура базы данных не найдена. Схемы и таблицы будут созданы")
                    reply_box.setIcon(QMessageBox.Information)
                    reply_box.setStyleSheet(self.message_box_style)
                    reply = reply_box.exec()

                    # Создание схемы и таблиц
                    if self.controller.initialize_database():
                        ok_box = QMessageBox(self)
                        ok_box.setWindowTitle("Успех")
                        ok_box.setText("Схема и таблицы успешно созданы")
                        ok_box.setIcon(QMessageBox.Information)
                        ok_box.setStyleSheet(self.message_box_style)
                        ok_box.exec()
                    else:
                        err_box = QMessageBox(self)
                        err_box.setWindowTitle("Ошибка")
                        err_box.setText("Не удалось создать схему базы данных")
                        err_box.setIcon(QMessageBox.Critical)
                        err_box.setStyleSheet(self.message_box_style)
                        err_box.exec()
                        return

                # Подключение успешно
                success_box = QMessageBox(self)
                success_box.setWindowTitle("Успех")
                success_box.setText("Подключение успешно установлено")
                success_box.setIcon(QMessageBox.Information)
                success_box.setStyleSheet(self.message_box_style)
                success_box.exec()
                self.accept()

            except Exception as e:
                # Ошибка при проверке структуры БД
                err_box = QMessageBox(self)
                err_box.setWindowTitle("Ошибка")
                err_box.setText(f"Ошибка при проверке структуры базы данных: {str(e)}")
                err_box.setIcon(QMessageBox.Critical)
                err_box.setStyleSheet(self.message_box_style)
                err_box.exec()
        else:
            # Ошибка подключения к БД
            err_box = QMessageBox(self)
            err_box.setWindowTitle("Ошибка")
            err_box.setText("Не удалось подключиться к базе данных. Проверьте параметры подключения.")
            err_box.setIcon(QMessageBox.Critical)
            err_box.setStyleSheet(self.message_box_style)
            err_box.exec()

    def create_database(self):
        """Создание новой базы данных с введенными параметрами."""
        # Получение параметров из полей ввода
        dbname = self.db_combo.currentText()
        host = self.host_edit.text()
        port = self.port_edit.text()
        user = self.user_edit.text()
        password = self.password_edit.text()

        # Проверка заполнения всех обязательных полей
        if not dbname or not host or not port or not user:
            warn_box = QMessageBox(self)
            warn_box.setWindowTitle("Ошибка")
            warn_box.setText("Все поля, кроме пароля, должны быть заполнены")
            warn_box.setIcon(QMessageBox.Warning)
            warn_box.setStyleSheet(self.message_box_style)
            warn_box.exec()
            return

        # Установка параметров подключения
        self.controller.set_connection_params(dbname, user, password, host, port)

        # Попытка создания базы данных
        if self.controller.create_database():
            # Запрос на создание схемы и таблиц
            reply_box = QMessageBox(self)
            reply_box.setWindowTitle("База данных создана")
            reply_box.setText("База данных успешно создана. Хотите создать схемы и таблицы?")
            reply_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            reply_box.setIcon(QMessageBox.Question)
            reply_box.setStyleSheet(self.message_box_style)
            reply = reply_box.exec()

            if reply == QMessageBox.Yes:
                # Подключение и инициализация базы данных
                if self.controller.connect_to_database() and self.controller.initialize_database():
                    success_box = QMessageBox(self)
                    success_box.setWindowTitle("Успех")
                    success_box.setText("База данных, схема и таблицы успешно созданы")
                    success_box.setIcon(QMessageBox.Information)
                    success_box.setStyleSheet(self.message_box_style)
                    success_box.exec()
                    self.accept()
                else:
                    err_box = QMessageBox(self)
                    err_box.setWindowTitle("Ошибка")
                    err_box.setText("Не удалось создать схему базы данных")
                    err_box.setIcon(QMessageBox.Critical)
                    err_box.setStyleSheet(self.message_box_style)
                    err_box.exec()
            else:
                # Пользователь отказался создавать схемы и таблицы
                return
        else:
            # Ошибка создания базы данных
            err_box = QMessageBox(self)
            err_box.setWindowTitle("Ошибка")
            err_box.setText("Не удалось создать базу данных")
            err_box.setIcon(QMessageBox.Critical)
            err_box.setStyleSheet(self.message_box_style)
            err_box.exec()


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
        self.setMinimumSize(900, 600)

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
        <p><b>5. Актёры</b> - добавляйте и удаляйте актеров</p>
        <p><b>6. Пропустить год</b> - продайте права на постановку и получите дополнительные средства</p>
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

        # Кнопка управления актерами
        self.actors_btn = QPushButton("Актеры")
        self.actors_btn.clicked.connect(self.manage_actors)
        buttons_layout.addWidget(self.actors_btn)

        # Кнопка пропуска года
        self.skip_year_btn = QPushButton("Пропустить год")
        self.skip_year_btn.clicked.connect(self.skip_year)
        buttons_layout.addWidget(self.skip_year_btn)

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
            if game_data:
                self.year_label.setText(f"Текущий год: {game_data['current_year']}")
                # Форматирование числа с разделителями тысяч
                self.capital_label.setText(f"Капитал: {game_data['capital']:,} ₽".replace(',', ' '))
        except Exception as e:
            self.logger.error(f"Ошибка при обновлении информации: {str(e)}")
            self.year_label.setText("Текущий год: —")
            self.capital_label.setText("Капитал: —")

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
        dialog = NewPerformanceDialog(self.controller, self)
        if dialog.exec():
            self.update_game_info()

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

    def manage_actors(self):
        """Открытие диалога управления актерами."""
        dialog = ActorsManagementDialog(self.controller, self)
        if dialog.exec():
            self.update_game_info()

    def skip_year(self):
        """Пропуск текущего года и получение дохода от продажи прав."""
        # Запрос подтверждения
        result = QMessageBox.question(
            self,
            "Пропустить год",
            "Вы уверены, что хотите пропустить год? Театр продаст права на постановку другому театру и получит случайную сумму (10-20% от капитала).",
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
                f"Театр получил {skip_result['rights_sale']:,} ₽ за продажу прав на постановку.".replace(',', ' ')
            )
            self.update_game_info()

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