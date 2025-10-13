"""
Модуль для тестирования подключения к базе данных PostgreSQL.
Используется для проверки корректности настроек подключения.
"""
import psycopg2
from logger import Logger


def test_db_connection(dbname="taskBD", user="artem", password="postgres", host="localhost", port="5432"):
    """
    Проверяет соединение с базой данных PostgreSQL.

    Args:
        dbname: Имя базы данных
        user: Имя пользователя
        password: Пароль
        host: Хост сервера БД
        port: Порт сервера БД

    Returns:
        tuple: (успех подключения (bool), сообщение/версия PostgreSQL (str))
    """
    logger = Logger()
    try:
        # Попытка подключения к базе данных
        connection = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port
        )
        cursor = connection.cursor()
        logger.info(f"Успешное подключение к базе данных {dbname}")

        # Проверка версии PostgreSQL
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        logger.info(f"Версия PostgreSQL: {version}")

        # Закрытие соединения
        cursor.close()
        connection.close()
        return True, version
    except psycopg2.Error as e:
        # Обработка ошибки подключения
        logger.error(f"Ошибка подключения к базе данных: {str(e)}")
        return False, str(e)


if __name__ == "__main__":
    # Запуск тестирования подключения
    success, message = test_db_connection()
    print(f"Результат тестирования: {'Успешно' if success else 'Ошибка'}")
    print(f"Сообщение: {message}")