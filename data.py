"""
Модуль для работы с данными театра в базе данных PostgreSQL.
Содержит классы для хранения, доступа и манипуляции данными.
"""
import psycopg2
from psycopg2 import sql, extensions
from psycopg2.extras import DictCursor
import enum
from datetime import datetime
from logger import Logger


class ActorRank(enum.Enum):
    """
    Перечисление званий актеров театра.
    Представляет собой иерархию от начинающего до народного артиста.
    """
    BEGINNER = "Начинающий"
    REGULAR = "Постоянный"
    LEAD = "Ведущий"
    MASTER = "Мастер"
    HONORED = "Заслуженный"
    PEOPLE = "Народный"

    @classmethod
    def from_value(cls, value):
        """Получение объекта перечисления по его значению."""
        for member in cls:
            if member.value == value:
                return member
        raise ValueError(f"'{value}' не является допустимым званием актера")

    @classmethod
    def compare(cls, rank1, rank2):
        """
        Сравнение двух званий.

        Returns:
            int: -1 если rank1 < rank2, 0 если равны, 1 если rank1 > rank2
        """
        r1 = cls.from_value(rank1)
        r2 = cls.from_value(rank2)

        if r1.value == r2.value:
            return 0

        rank_order = [cls.BEGINNER, cls.REGULAR, cls.LEAD, cls.MASTER, cls.HONORED, cls.PEOPLE]
        idx1 = rank_order.index(r1)
        idx2 = rank_order.index(r2)

        return -1 if idx1 < idx2 else 1


class DatabaseManager:
    """
    Менеджер базы данных театра.
    Отвечает за взаимодействие с PostgreSQL, выполнение запросов
    и преобразование данных.
    """

    def __init__(self):
        """Инициализация менеджера БД."""
        self.logger = Logger()
        self.connection_params = None
        self.connection = None
        self.cursor = None

    def set_connection_params(self, dbname, user, password, host, port):
        """Установка параметров подключения к базе данных."""
        self.connection_params = {
            "dbname": dbname,
            "user": user,
            "password": password,
            "host": host,
            "port": port
        }
        self.logger.info(f"Установлены параметры подключения: {dbname}@{host}:{port}")

    def connect(self):
        """
        Подключение к базе данных с использованием установленных параметров.

        Returns:
            bool: Успешность подключения
        """
        if self.connection_params is None:
            self.logger.error("Параметры подключения не установлены")
            return False

        try:
            self.connection = psycopg2.connect(**self.connection_params)
            self.cursor = self.connection.cursor(cursor_factory=DictCursor)
            self.logger.info(f"Подключение к БД {self.connection_params['dbname']} успешно")
            return True
        except psycopg2.Error as e:
            self.logger.error(f"Ошибка подключения к БД: {str(e)}")
            return False

    def connect_to_postgres(self):
        """
        Подключение к системной базе данных postgres для создания новой БД.

        Returns:
            tuple: (соединение, курсор) или (None, None) при ошибке
        """
        if self.connection_params is None:
            self.logger.error("Параметры подключения не установлены")
            return False

        try:
            # Копируем параметры и меняем имя БД на 'postgres'
            postgres_params = self.connection_params.copy()
            postgres_params["dbname"] = "postgres"

            conn = psycopg2.connect(**postgres_params)
            conn.autocommit = True
            cursor = conn.cursor()
            self.logger.info(f"Подключение к системной БД postgres успешно")
            return conn, cursor
        except psycopg2.Error as e:
            self.logger.error(f"Ошибка подключения к системной БД postgres: {str(e)}")
            return None, None

    def create_database(self):
        """
        Создание новой базы данных если она не существует.

        Returns:
            bool: Успешность создания БД
        """
        try:
            conn, cursor = self.connect_to_postgres()
            if not conn:
                return False

            dbname = self.connection_params["dbname"]

            # Проверяем существование БД
            cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
            exists = cursor.fetchone()

            if not exists:
                # Создаем БД если она не существует
                cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(dbname)))
                self.logger.info(f"База данных {dbname} успешно создана")
            else:
                self.logger.info(f"База данных {dbname} уже существует")

            cursor.close()
            conn.close()
            return True
        except psycopg2.Error as e:
            self.logger.error(f"Ошибка создания БД: {str(e)}")
            return False

    def disconnect(self):
        """Закрытие соединения с базой данных."""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
            self.logger.info("Соединение с БД закрыто")

    def create_schema(self):
        """
        Создание схемы базы данных с таблицами и типами данных.

        Returns:
            bool: Успешность создания схемы
        """
        try:
            # Создание типа перечисления для званий актеров
            self.cursor.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'actor_rank') THEN
                        CREATE TYPE actor_rank AS ENUM (
                            'Начинающий', 'Постоянный', 'Ведущий', 'Мастер', 'Заслуженный', 'Народный'
                        );
                    END IF;
                END$$;
            """)

            # Создание таблицы актеров
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS actors (
                    actor_id SERIAL PRIMARY KEY,
                    last_name VARCHAR(100) NOT NULL,
                    first_name VARCHAR(100) NOT NULL,
                    patronymic VARCHAR(100),
                    rank actor_rank NOT NULL DEFAULT 'Начинающий',
                    awards_count INTEGER NOT NULL DEFAULT 0 CHECK (awards_count >= 0),
                    experience INTEGER NOT NULL DEFAULT 0 CHECK (experience >= 0),
                    CONSTRAINT actor_full_name_unique UNIQUE (last_name, first_name, patronymic)
                );
            """)

            # Создание таблицы сюжетов
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS plots (
                    plot_id SERIAL PRIMARY KEY,
                    title VARCHAR(200) NOT NULL UNIQUE,
                    minimum_budget INTEGER NOT NULL CHECK (minimum_budget > 0),
                    production_cost INTEGER NOT NULL CHECK (production_cost > 0),
                    roles_count INTEGER NOT NULL CHECK (roles_count >= 1),
                    demand INTEGER NOT NULL CHECK (demand BETWEEN 1 AND 10),
                    required_ranks actor_rank[] NOT NULL DEFAULT ARRAY['Начинающий']::actor_rank[]
                );
            """)

            # Создание таблицы спектаклей
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS performances (
                    performance_id SERIAL PRIMARY KEY,
                    title VARCHAR(200) NOT NULL,
                    plot_id INTEGER NOT NULL,
                    year INTEGER NOT NULL CHECK (year >= 2022),
                    budget INTEGER NOT NULL CHECK (budget > 0),
                    revenue INTEGER DEFAULT 0 CHECK (revenue >= 0),
                    is_completed BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (plot_id) REFERENCES plots(plot_id) ON DELETE RESTRICT,
                    CONSTRAINT unique_performance_per_year UNIQUE(year)
                );
            """)

            # Создание таблицы связей между актерами и спектаклями
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS actor_performances (
                    actor_id INTEGER NOT NULL,
                    performance_id INTEGER NOT NULL,
                    role VARCHAR(100) NOT NULL,
                    contract_cost INTEGER NOT NULL CHECK (contract_cost > 0),
                    PRIMARY KEY (actor_id, performance_id),
                    FOREIGN KEY (actor_id) REFERENCES actors(actor_id) ON DELETE RESTRICT,
                    FOREIGN KEY (performance_id) REFERENCES performances(performance_id) ON DELETE CASCADE
                );
            """)

            # Создание таблицы с игровыми данными
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS game_data (
                    id INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
                    current_year INTEGER NOT NULL DEFAULT 2025 CHECK (current_year >= 2022),
                    capital BIGINT NOT NULL DEFAULT 1000000 CHECK (capital >= 0)
                );
            """)

            self.connection.commit()
            self.logger.info("Схема БД успешно создана")
            return True
        except psycopg2.Error as e:
            self.connection.rollback()
            self.logger.error(f"Ошибка создания схемы БД: {str(e)}")
            return False

    def init_sample_data(self):
        """
        Инициализация БД тестовыми данными.

        Returns:
            bool: Успешность инициализации
        """
        try:
            # Добавление игровых данных
            self.cursor.execute("""
                INSERT INTO game_data (id, current_year, capital)
                VALUES (1, 2025, 1000000)
                ON CONFLICT (id) DO UPDATE
                SET current_year = 2025, capital = 1000000
            """)

            # Добавление тестовых актеров
            actors = [
                ('Иванов', 'Иван', 'Иванович', 'Ведущий', 3, 5),
                ('Петров', 'Петр', 'Петрович', 'Заслуженный', 5, 10),
                ('Сидорова', 'Анна', 'Сергеевна', 'Народный', 8, 15),
                ('Смирнов', 'Алексей', 'Игоревич', 'Мастер', 4, 8),
                ('Козлова', 'Екатерина', 'Дмитриевна', 'Постоянный', 2, 4),
                ('Морозов', 'Дмитрий', 'Александрович', 'Начинающий', 0, 2),
                ('Новикова', 'Ольга', 'Владимировна', 'Постоянный', 1, 3),
                ('Соколов', 'Владимир', 'Михайлович', 'Ведущий', 3, 7),
                ('Попова', 'Мария', 'Андреевна', 'Мастер', 5, 9),
                ('Лебедев', 'Сергей', 'Николаевич', 'Заслуженный', 6, 12)
            ]

            for actor in actors:
                self.cursor.execute("""
                    INSERT INTO actors (last_name, first_name, patronymic, rank, awards_count, experience)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (last_name, first_name, patronymic) DO NOTHING
                """, actor)

            # Добавление тестовых сюжетов
            plots = [
                ('Ромео и Джульетта', 500000, 350000, 6, 8, ['Ведущий', 'Мастер']),
                ('Гамлет', 800000, 500000, 8, 9, ['Мастер', 'Заслуженный']),
                ('Чайка', 400000, 250000, 5, 7, ['Постоянный', 'Ведущий']),
                ('Вишневый сад', 600000, 400000, 7, 8, ['Ведущий', 'Мастер']),
                ('Три сестры', 550000, 350000, 6, 7, ['Постоянный', 'Ведущий']),
                ('Отелло', 700000, 450000, 7, 9, ['Мастер', 'Заслуженный']),
                ('Ревизор', 450000, 300000, 6, 7, ['Ведущий']),
                ('Горе от ума', 500000, 350000, 7, 8, ['Ведущий', 'Мастер']),
                ('Дядя Ваня', 400000, 250000, 5, 6, ['Постоянный']),
                ('Маскарад', 650000, 400000, 8, 8, ['Мастер'])
            ]

            for plot in plots:
                self.cursor.execute("""
                    INSERT INTO plots (title, minimum_budget, production_cost, roles_count, demand, required_ranks)
                    VALUES (%s, %s, %s, %s, %s, %s::actor_rank[])
                    ON CONFLICT (title) DO NOTHING
                """, plot)

            # Добавление тестовых постановок
            past_performances = [
                ('Ромео и Джульетта в современном мире', 1, 2022, 600000, 950000, True),
                ('Гамлет: Перезагрузка', 2, 2023, 850000, 1200000, True),
                ('Чайка над морем', 3, 2024, 500000, 780000, True)
            ]

            for perf in past_performances:
                self.cursor.execute("""
                    INSERT INTO performances (title, plot_id, year, budget, revenue, is_completed)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (year) DO NOTHING
                """, perf)

            # Добавление связей актеров с постановками
            actor_perfs = [
                (1, 1, 'Ромео', 100000),
                (5, 1, 'Джульетта', 90000),
                (8, 1, 'Меркуцио', 80000),
                (4, 1, 'Тибальт', 70000),
                (7, 1, 'Кормилица', 60000),
                (6, 1, 'Бенволио', 50000),

                (2, 2, 'Гамлет', 150000),
                (9, 2, 'Офелия', 120000),
                (8, 2, 'Клавдий', 110000),
                (7, 2, 'Гертруда', 100000),
                (4, 2, 'Полоний', 90000),
                (6, 2, 'Горацио', 80000),
                (1, 2, 'Лаэрт', 80000),
                (5, 2, 'Розенкранц', 70000),

                (3, 3, 'Нина Заречная', 130000),
                (2, 3, 'Константин Треплев', 120000),
                (9, 3, 'Ирина Аркадина', 110000),
                (4, 3, 'Борис Тригорин', 100000),
                (7, 3, 'Маша', 90000)
            ]

            for ap in actor_perfs:
                self.cursor.execute("""
                    INSERT INTO actor_performances (actor_id, performance_id, role, contract_cost)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (actor_id, performance_id) DO NOTHING
                """, ap)

            self.connection.commit()
            self.logger.info("Тестовые данные успешно добавлены")
            return True
        except psycopg2.Error as e:
            self.connection.rollback()
            self.logger.error(f"Ошибка добавления тестовых данных: {str(e)}")
            return False

    def reset_database(self):
        """
        Сброс всей базы данных к начальному состоянию.

        Returns:
            bool: Успешность сброса
        """
        try:
            # Очистка всех таблиц
            self.cursor.execute("TRUNCATE TABLE actor_performances CASCADE")
            self.cursor.execute("TRUNCATE TABLE performances CASCADE")
            self.cursor.execute("TRUNCATE TABLE actors CASCADE")
            self.cursor.execute("TRUNCATE TABLE plots CASCADE")
            self.cursor.execute("TRUNCATE TABLE game_data CASCADE")

            # Сброс последовательностей идентификаторов
            self.cursor.execute("ALTER SEQUENCE actors_actor_id_seq RESTART WITH 1")
            self.cursor.execute("ALTER SEQUENCE plots_plot_id_seq RESTART WITH 1")
            self.cursor.execute("ALTER SEQUENCE performances_performance_id_seq RESTART WITH 1")

            # Инициализация тестовыми данными
            self.init_sample_data()

            self.connection.commit()
            self.logger.info("База данных успешно сброшена")
            return True
        except psycopg2.Error as e:
            self.connection.rollback()
            self.logger.error(f"Ошибка сброса БД: {str(e)}")
            return False

    def reset_schema(self):
        """
        Сброс схемы базы данных (удаление всех таблиц и типов).

        Returns:
            bool: Успешность сброса
        """
        try:
            # Удаление всех таблиц и типов
            self.cursor.execute("""
                DROP TABLE IF EXISTS actor_performances CASCADE;
                DROP TABLE IF EXISTS performances CASCADE;
                DROP TABLE IF EXISTS actors CASCADE;
                DROP TABLE IF EXISTS plots CASCADE;
                DROP TABLE IF EXISTS game_data CASCADE;
                DROP TYPE IF EXISTS actor_rank CASCADE;
            """)
            self.connection.commit()
            self.logger.info("Схема БД успешно удалена")

            # Создание новой схемы
            success = self.create_schema()

            return success
        except psycopg2.Error as e:
            self.connection.rollback()
            self.logger.error(f"Ошибка сброса схемы БД: {str(e)}")
            return False

    def get_actors(self):
        """
        Получение списка всех актеров.

        Returns:
            list: Список словарей с данными актеров
        """
        try:
            self.cursor.execute("SELECT * FROM actors ORDER BY actor_id")
            return self.cursor.fetchall()
        except psycopg2.Error as e:
            self.logger.error(f"Ошибка получения списка актеров: {str(e)}")
            return []

    def get_plots(self):
        """
        Получение списка всех сюжетов.

        Returns:
            list: Список словарей с данными сюжетов
        """
        try:
            self.cursor.execute("SELECT * FROM plots ORDER BY title")
            return self.cursor.fetchall()
        except psycopg2.Error as e:
            self.logger.error(f"Ошибка получения списка сюжетов: {str(e)}")
            return []

    def get_performances(self, year=None):
        """
        Получение списка всех спектаклей с возможностью фильтрации по году.

        Args:
            year: Год для фильтрации (опционально)

        Returns:
            list: Список словарей с данными спектаклей
        """
        try:
            if year:
                # Запрос с фильтрацией по году
                self.cursor.execute("""
                    SELECT p.*, pl.title as plot_title 
                    FROM performances p
                    JOIN plots pl ON p.plot_id = pl.plot_id
                    WHERE p.year = %s
                """, (year,))
            else:
                # Запрос всех спектаклей
                self.cursor.execute("""
                    SELECT p.*, pl.title as plot_title 
                    FROM performances p
                    JOIN plots pl ON p.plot_id = pl.plot_id
                    ORDER BY p.year DESC
                """)
            return self.cursor.fetchall()
        except psycopg2.Error as e:
            self.logger.error(f"Ошибка получения спектаклей: {str(e)}")
            return []

    def get_actors_in_performance(self, performance_id):
        """
        Получение списка актеров, участвующих в спектакле.

        Args:
            performance_id: ID спектакля

        Returns:
            list: Список словарей с данными актеров и их ролей
        """
        try:
            self.cursor.execute("""
                SELECT a.*, ap.role, ap.contract_cost
                FROM actors a
                JOIN actor_performances ap ON a.actor_id = ap.actor_id
                WHERE ap.performance_id = %s
                ORDER BY ap.contract_cost DESC
            """, (performance_id,))
            return self.cursor.fetchall()
        except psycopg2.Error as e:
            self.logger.error(f"Ошибка получения актеров в спектакле: {str(e)}")
            return []

    def get_game_data(self):
        """
        Получение игровых данных (текущий год и капитал).

        Returns:
            dict: Словарь с игровыми данными
        """
        try:
            self.cursor.execute("SELECT * FROM game_data WHERE id = 1")
            return self.cursor.fetchone()
        except psycopg2.Error as e:
            self.logger.error(f"Ошибка получения игровых данных: {str(e)}")
            return None

    def add_plot(self, title, minimum_budget, production_cost, roles_count, demand, required_ranks):
        """
        Добавление нового сюжета в базу данных.

        Args:
            title: Название сюжета
            minimum_budget: Минимальный бюджет
            production_cost: Стоимость постановки
            roles_count: Количество ролей
            demand: Спрос (1-10)
            required_ranks: Список минимальных званий для ролей

        Returns:
            int or None: ID добавленного сюжета или None при ошибке
        """
        try:
            self.cursor.execute("""
                INSERT INTO plots (title, minimum_budget, production_cost, roles_count, demand, required_ranks)
                VALUES (%s, %s, %s, %s, %s, %s::actor_rank[])
                RETURNING plot_id
            """, (title, minimum_budget, production_cost, roles_count, demand, required_ranks))
            plot_id = self.cursor.fetchone()[0]
            self.connection.commit()
            self.logger.info(f"Добавлен сюжет с ID {plot_id}")
            return plot_id
        except psycopg2.Error as e:
            self.connection.rollback()
            self.logger.error(f"Ошибка добавления сюжета: {str(e)}")
            return None

    def update_plot(self, plot_id, title, minimum_budget, production_cost, roles_count, demand, required_ranks):
        """
        Обновление данных сюжета.

        Args:
            plot_id: ID сюжета
            title: Название сюжета
            minimum_budget: Минимальный бюджет
            production_cost: Стоимость постановки
            roles_count: Количество ролей
            demand: Спрос (1-10)
            required_ranks: Список минимальных званий для ролей

        Returns:
            tuple: (успех операции (bool), сообщение об ошибке (str))
        """
        try:
            self.cursor.execute("""
                UPDATE plots
                SET title = %s, minimum_budget = %s, production_cost = %s, 
                    roles_count = %s, demand = %s, required_ranks = %s::actor_rank[]
                WHERE plot_id = %s
                RETURNING plot_id
            """, (title, minimum_budget, production_cost, roles_count, demand, required_ranks, plot_id))

            updated_id = self.cursor.fetchone()
            if not updated_id:
                self.logger.error(f"Сюжет с ID {plot_id} не найден")
                return False, "Сюжет не найден"

            self.connection.commit()
            self.logger.info(f"Обновлен сюжет с ID {plot_id}")
            return True, ""
        except psycopg2.Error as e:
            self.connection.rollback()
            self.logger.error(f"Ошибка обновления сюжета: {str(e)}")
            return False, str(e)

    def delete_plot(self, plot_id):
        """
        Удаление сюжета из базы данных.

        Args:
            plot_id: ID сюжета

        Returns:
            tuple: (успех операции (bool), сообщение об ошибке (str))
        """
        try:
            # Проверка использования сюжета в спектаклях
            self.cursor.execute("""
                SELECT COUNT(*) FROM performances
                WHERE plot_id = %s
            """, (plot_id,))

            if self.cursor.fetchone()[0] > 0:
                self.logger.error(f"Сюжет с ID {plot_id} используется в спектаклях")
                return False, "Сюжет используется в спектаклях и не может быть удален"

            # Проверка минимального количества сюжетов
            self.cursor.execute("SELECT COUNT(*) FROM plots")
            if self.cursor.fetchone()[0] <= 5:
                self.logger.error("Невозможно удалить сюжет: минимальное число сюжетов - 5")
                return False, "Минимальное число сюжетов - 5"

            # Удаление сюжета
            self.cursor.execute("DELETE FROM plots WHERE plot_id = %s", (plot_id,))
            self.connection.commit()
            self.logger.info(f"Удален сюжет с ID {plot_id}")
            return True, ""
        except psycopg2.Error as e:
            self.connection.rollback()
            self.logger.error(f"Ошибка удаления сюжета: {str(e)}")
            return False, str(e)

    def update_game_data(self, year, capital):
        """
        Обновление игровых данных.

        Args:
            year: Новый текущий год
            capital: Новый капитал

        Returns:
            bool: Успешность обновления
        """
        try:
            self.cursor.execute("""
                UPDATE game_data
                SET current_year = %s, capital = %s
                WHERE id = 1
            """, (year, capital))
            self.connection.commit()
            self.logger.info(f"Обновлены игровые данные: год={year}, капитал={capital}")
            return True
        except psycopg2.Error as e:
            self.connection.rollback()
            self.logger.error(f"Ошибка обновления игровых данных: {str(e)}")
            return False

    def add_actor(self, last_name, first_name, patronymic, rank, awards_count, experience):
        """
        Добавление нового актера в базу данных.

        Args:
            last_name: Фамилия
            first_name: Имя
            patronymic: Отчество
            rank: Звание актера
            awards_count: Количество наград
            experience: Опыт работы в годах

        Returns:
            int or None: ID добавленного актера или None при ошибке
        """
        try:
            self.cursor.execute("""
                INSERT INTO actors (last_name, first_name, patronymic, rank, awards_count, experience)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING actor_id
            """, (last_name, first_name, patronymic, rank, awards_count, experience))
            actor_id = self.cursor.fetchone()[0]
            self.connection.commit()
            self.logger.info(f"Добавлен актер с ID {actor_id}")
            return actor_id
        except psycopg2.Error as e:
            self.connection.rollback()
            self.logger.error(f"Ошибка добавления актера: {str(e)}")
            return None

    def update_actor(self, actor_id, last_name, first_name, patronymic, rank, awards_count, experience):
        """
        Обновление данных актера.

        Args:
            actor_id: ID актера
            last_name: Фамилия
            first_name: Имя
            patronymic: Отчество
            rank: Звание актера
            awards_count: Количество наград
            experience: Опыт работы в годах

        Returns:
            tuple: (успех операции (bool), сообщение об ошибке (str))
        """
        try:
            self.cursor.execute("""
                UPDATE actors
                SET last_name = %s, first_name = %s, patronymic = %s, 
                    rank = %s, awards_count = %s, experience = %s
                WHERE actor_id = %s
                RETURNING actor_id
            """, (last_name, first_name, patronymic, rank, awards_count, experience, actor_id))

            updated_id = self.cursor.fetchone()
            if not updated_id:
                self.logger.error(f"Актер с ID {actor_id} не найден")
                return False, "Актер не найден"

            self.connection.commit()
            self.logger.info(f"Обновлен актер с ID {actor_id}")
            return True, ""
        except psycopg2.Error as e:
            self.connection.rollback()
            self.logger.error(f"Ошибка обновления актера: {str(e)}")
            return False, str(e)

    def delete_actor(self, actor_id):
        """
        Удаление актера из базы данных.

        Args:
            actor_id: ID актера

        Returns:
            tuple: (успех операции (bool), сообщение об ошибке (str))
        """
        try:
            # Проверка участия актера ТОЛЬКО в текущих постановках
            self.cursor.execute("""
                SELECT COUNT(*) FROM actor_performances ap
                JOIN performances p ON ap.performance_id = p.performance_id
                WHERE ap.actor_id = %s AND p.is_completed = FALSE
            """, (actor_id,))

            if self.cursor.fetchone()[0] > 0:
                self.logger.error(f"Актер с ID {actor_id} занят в текущих постановках")
                return False, "Актер занят в текущих постановках"

            # Проверка минимального количества актеров
            self.cursor.execute("SELECT COUNT(*) FROM actors")
            if self.cursor.fetchone()[0] <= 8:
                self.logger.error("Невозможно удалить актера: минимальное число актеров - 8")
                return False, "Минимальное число актеров - 8"

            # Удаление всех связей с прошлыми постановками
            self.cursor.execute("""
                DELETE FROM actor_performances 
                WHERE actor_id = %s AND performance_id IN (
                    SELECT performance_id FROM performances WHERE is_completed = TRUE
                )
            """, (actor_id,))

            # Теперь удаляем самого актера
            self.cursor.execute("DELETE FROM actors WHERE actor_id = %s", (actor_id,))
            self.connection.commit()
            self.logger.info(f"Удален актер с ID {actor_id}")
            return True, ""
        except psycopg2.Error as e:
            self.connection.rollback()
            self.logger.error(f"Ошибка удаления актера: {str(e)}")
            return False, str(e)

    def create_performance(self, title, plot_id, year, budget):
        """
        Создание нового спектакля.

        Args:
            title: Название спектакля
            plot_id: ID сюжета
            year: Год постановки
            budget: Бюджет спектакля

        Returns:
            int or None: ID созданного спектакля или None при ошибке
        """
        try:
            self.cursor.execute("""
                INSERT INTO performances (title, plot_id, year, budget, is_completed)
                VALUES (%s, %s, %s, %s, FALSE)
                RETURNING performance_id
            """, (title, plot_id, year, budget))
            performance_id = self.cursor.fetchone()[0]
            self.connection.commit()
            self.logger.info(f"Создан спектакль с ID {performance_id}")
            return performance_id
        except psycopg2.Error as e:
            self.connection.rollback()
            self.logger.error(f"Ошибка создания спектакля: {str(e)}")
            return None

    def assign_actor_to_role(self, actor_id, performance_id, role, contract_cost):
        """
        Назначение актера на роль в спектакле.

        Args:
            actor_id: ID актера
            performance_id: ID спектакля
            role: Название роли
            contract_cost: Стоимость контракта

        Returns:
            bool: Успешность назначения
        """
        try:
            self.cursor.execute("""
                INSERT INTO actor_performances (actor_id, performance_id, role, contract_cost)
                VALUES (%s, %s, %s, %s)
            """, (actor_id, performance_id, role, contract_cost))
            self.connection.commit()
            self.logger.info(f"Актер {actor_id} назначен на роль '{role}' в спектакле {performance_id}")
            return True
        except psycopg2.Error as e:
            self.connection.rollback()
            self.logger.error(f"Ошибка назначения актера: {str(e)}")
            return False

    def complete_performance(self, performance_id, revenue):
        """
        Завершение спектакля с указанием выручки.

        Args:
            performance_id: ID спектакля
            revenue: Полученная выручка

        Returns:
            bool: Успешность завершения
        """
        try:
            # Установка флага завершения и выручки
            self.cursor.execute("""
                UPDATE performances
                SET revenue = %s, is_completed = TRUE
                WHERE performance_id = %s
            """, (revenue, performance_id))

            # Увеличение опыта актеров, участвовавших в спектакле
            self.cursor.execute("""
                UPDATE actors a
                SET experience = a.experience + 1
                FROM actor_performances ap
                WHERE a.actor_id = ap.actor_id AND ap.performance_id = %s
            """, (performance_id,))

            self.connection.commit()
            self.logger.info(f"Спектакль {performance_id} завершен с выручкой {revenue}")
            return True
        except psycopg2.Error as e:
            self.connection.rollback()
            self.logger.error(f"Ошибка завершения спектакля: {str(e)}")
            return False

    def update_performance_budget(self, performance_id, budget):
        """
        Обновление бюджета спектакля.

        Args:
            performance_id: ID спектакля
            budget: Новый бюджет

        Returns:
            bool: Успешность обновления
        """
        try:
            self.cursor.execute("""
                UPDATE performances
                SET budget = %s
                WHERE performance_id = %s
            """, (budget, performance_id))
            self.connection.commit()
            self.logger.info(f"Обновлен бюджет спектакля {performance_id}: {budget}")
            return True
        except psycopg2.Error as e:
            self.connection.rollback()
            self.logger.error(f"Ошибка обновления бюджета: {str(e)}")
            return False

    def upgrade_actor_rank(self, actor_id):
        """
        Повышение звания актера на одну ступень.

        Args:
            actor_id: ID актера

        Returns:
            bool: Успешность повышения
        """
        try:
            # Получение текущего звания
            self.cursor.execute("SELECT rank FROM actors WHERE actor_id = %s", (actor_id,))
            current_rank = self.cursor.fetchone()[0]

            # Определение нового звания
            rank_order = list(ActorRank)
            rank_idx = [r.value for r in rank_order].index(current_rank)

            # Повышение звания, если это возможно
            if rank_idx < len(rank_order) - 1:
                new_rank = rank_order[rank_idx + 1].value
                self.cursor.execute("""
                    UPDATE actors
                    SET rank = %s
                    WHERE actor_id = %s
                """, (new_rank, actor_id))
                self.connection.commit()
                self.logger.info(f"Актер {actor_id} повышен до звания '{new_rank}'")
                return True
            else:
                self.logger.info(f"Актер {actor_id} уже имеет максимальное звание")
                return False
        except psycopg2.Error as e:
            self.connection.rollback()
            self.logger.error(f"Ошибка повышения звания: {str(e)}")
            return False

    def award_actor(self, actor_id):
        """
        Присвоение награды актеру.

        Args:
            actor_id: ID актера

        Returns:
            bool: Успешность присвоения
        """
        try:
            self.cursor.execute("""
                UPDATE actors
                SET awards_count = awards_count + 1
                WHERE actor_id = %s
            """, (actor_id,))
            self.connection.commit()
            self.logger.info(f"Актеру {actor_id} присвоена награда")
            return True
        except psycopg2.Error as e:
            self.connection.rollback()
            self.logger.error(f"Ошибка присвоения награды: {str(e)}")
            return False