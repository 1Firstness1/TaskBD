"""
Модуль диалога входа в приложение "Театральный менеджер".
Содержит класс для окна авторизации и подключения к базе данных.
"""
from PySide6.QtWidgets import (QDialog, QLabel, QVBoxLayout, QHBoxLayout, QFormLayout,
                              QComboBox, QLineEdit, QPushButton, QMessageBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIntValidator

from controller import TheaterController, ValidatedLineEdit
from logger import Logger


class ValidatedLoginLineEdit(ValidatedLineEdit):
    """
    Поле ввода с валидацией для окна логина.
    Разрешает только определенные символы.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(TheaterController(), *args, **kwargs)


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