"""
Главный модуль приложения "Театральный менеджер".
Точка входа в программу.
"""
import sys
from PySide6.QtWidgets import QApplication
from mainwindow import MainWindow
from login_d import LoginDialog
from logger import Logger

if __name__ == "__main__":
    # Инициализация логгера
    logger = Logger()
    logger.info("Запуск приложения")

    # Создание и настройка приложения Qt
    app = QApplication(sys.argv)
    app.setApplicationName("Театральный менеджер")

    # Показ диалога авторизации
    login_dialog = LoginDialog()
    if login_dialog.exec():
        # Если авторизация успешна, открываем главное окно
        window = MainWindow(login_dialog.controller)
        window.show()
        sys.exit(app.exec())
    else:
        # Если авторизация отменена, выходим из приложения
        sys.exit(0)