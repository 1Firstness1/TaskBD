"""
Модуль для работы с данными театра в базе данных PostgreSQL.
Содержит классы для хранения, доступа и манипуляции данными.
"""
import psycopg2
from psycopg2 import sql, extensions
from psycopg2.extras import DictCursor
import enum
from datetime import datetime, date
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
            self.connection = psycopg2.connect(**self.connection_params, client_encoding='UTF8')
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
            postgres_params = self.connection_params.copy()
            postgres_params["dbname"] = "postgres"

            conn = psycopg2.connect(**postgres_params, client_encoding='UTF8')
            conn.autocommit = True
            cursor = conn.cursor()
            self.logger.info("Подключение к системной БД postgres успешно")
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

            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
            exists = cursor.fetchone()

            if not exists:
                cursor.execute(
                    sql.SQL(
                        "CREATE DATABASE {} ENCODING 'UTF8' LC_COLLATE 'ru_RU.UTF-8' LC_CTYPE 'ru_RU.UTF-8' TEMPLATE template0"
                    ).format(sql.Identifier(dbname))
                )
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
            # Тип перечисления для званий актеров
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

            # Таблица актеров
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

            # Таблица сюжетов
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

            # Таблица спектаклей
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

            # Связи актеров и спектаклей
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

            # Игровые данные
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
            # Игровые данные
            self.cursor.execute("""
                INSERT INTO game_data (id, current_year, capital)
                VALUES (1, 2025, 1000000)
                ON CONFLICT (id) DO UPDATE
                SET current_year = 2025, capital = 1000000
            """)

            # Актеры
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

            # Сюжеты
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

            # Прошлые постановки
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

            # Участники постановок
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
            self.cursor.execute("TRUNCATE TABLE actor_performances CASCADE")
            self.cursor.execute("TRUNCATE TABLE performances CASCADE")
            self.cursor.execute("TRUNCATE TABLE actors CASCADE")
            self.cursor.execute("TRUNCATE TABLE plots CASCADE")
            self.cursor.execute("TRUNCATE TABLE game_data CASCADE")

            self.cursor.execute("ALTER SEQUENCE actors_actor_id_seq RESTART WITH 1")
            self.cursor.execute("ALTER SEQUENCE plots_plot_id_seq RESTART WITH 1")
            self.cursor.execute("ALTER SEQUENCE performances_performance_id_seq RESTART WITH 1")

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
            self.connection.rollback()
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
            self.connection.rollback()
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
                self.cursor.execute("""
                    SELECT p.*, pl.title as plot_title 
                    FROM performances p
                    JOIN plots pl ON p.plot_id = pl.plot_id
                    WHERE p.year = %s
                """, (year,))
            else:
                self.cursor.execute("""
                    SELECT p.*, pl.title as plot_title 
                    FROM performances p
                    JOIN plots pl ON p.plot_id = pl.plot_id
                    ORDER BY p.year DESC
                """)
            return self.cursor.fetchall()
        except psycopg2.Error as e:
            self.logger.error(f"Ошибка получения спектаклей: {str(e)}")
            self.connection.rollback()
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
            self.connection.rollback()
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
            self.connection.rollback()
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
            self.cursor.execute("""
                SELECT COUNT(*) FROM performances
                WHERE plot_id = %s
            """, (plot_id,))

            if self.cursor.fetchone()[0] > 0:
                self.logger.error(f"Сюжет с ID {plot_id} используется в спектаклях")
                return False, "Сюжет используется в спектаклях и не может быть удален"

            self.cursor.execute("SELECT COUNT(*) FROM plots")
            if self.cursor.fetchone()[0] <= 5:
                self.logger.error("Невозможно удалить сюжет: минимальное число сюжетов - 5")
                return False, "Минимальное число сюжетов - 5"

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
            self.cursor.execute("""
                SELECT COUNT(*) FROM actor_performances ap
                JOIN performances p ON ap.performance_id = p.performance_id
                WHERE ap.actor_id = %s AND p.is_completed = FALSE
            """, (actor_id,))

            if self.cursor.fetchone()[0] > 0:
                self.logger.error(f"Актер с ID {actor_id} занят в текущих постановках")
                return False, "Актер занят в текущих постановках"

            self.cursor.execute("SELECT COUNT(*) FROM actors")
            if self.cursor.fetchone()[0] <= 8:
                self.logger.error("Невозможно удалить актера: минимальное число актеров - 8")
                return False, "Минимальное число актеров - 8"

            self.cursor.execute("""
                DELETE FROM actor_performances 
                WHERE actor_id = %s AND performance_id IN (
                    SELECT performance_id FROM performances WHERE is_completed = TRUE
                )
            """, (actor_id,))

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
            self.cursor.execute("""
                UPDATE performances
                SET revenue = %s, is_completed = TRUE
                WHERE performance_id = %s
            """, (revenue, performance_id))

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
            self.cursor.execute("SELECT rank FROM actors WHERE actor_id = %s", (actor_id,))
            current_rank = self.cursor.fetchone()[0]

            rank_order = list(ActorRank)
            rank_idx = [r.value for r in rank_order].index(current_rank)

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

    # ============ Методы для TaskDialog ============

    def get_all_table_names(self):
        """
        Получение списка всех таблиц в БД (кроме служебных и основных игровых таблиц).

        Returns:
            list: Список имен таблиц
        """
        try:
            self.cursor.execute(
                """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                AND table_name NOT IN ('actors', 'performances', 'plots', 'game_data', 'actor_performances')
                ORDER BY table_name
                """
            )
            return [row[0] for row in self.cursor.fetchall()]
        except psycopg2.Error as e:
            self.logger.error(f"Ошибка получения списка таблиц: {str(e)}")
            self.connection.rollback()
            return []

    def get_table_columns(self, table_name):
        """
        Получение списка столбцов таблицы с информацией о типах.

        Args:
            table_name: Имя таблицы

        Returns:
            list: Список словарей с информацией о столбцах
        """
        try:
            self.cursor.execute(
                """
                SELECT 
                    column_name, 
                    data_type, 
                    is_nullable,
                    column_default,
                    character_maximum_length
                FROM information_schema.columns 
                WHERE table_name = %s
                ORDER BY ordinal_position
                """,
                (table_name,),
            )

            columns = []
            for row in self.cursor.fetchall():
                columns.append({
                    'name': row[0],
                    'type': row[1],
                    'nullable': row[2] == 'YES',
                    'default': row[3],
                    'max_length': row[4]
                })
            return columns
        except psycopg2.Error as e:
            self.logger.error(f"Ошибка получения столбцов таблицы {table_name}: {str(e)}")
            self.connection.rollback()
            return []

    def execute_select_query(self, query, params=None):
        """
        Выполнение SELECT запроса.

        Args:
            query: SQL запрос
            params: Параметры запроса (опционально)

        Returns:
            list: Результаты запроса
        """
        try:
            if not query or not query.strip():
                self.logger.warning("Попытка выполнить пустой запрос")
                return []

            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            return self.cursor.fetchall()
        except psycopg2.Error as e:
            self.logger.error(f"Ошибка выполнения SELECT запроса: {str(e)}")
            self.connection.rollback()
            return []

    def execute_update_query(self, query, params=None):
        """
        Выполнение произвольного UPDATE/DDL запроса.

        Args:
            query: SQL запрос
            params: Параметры запроса

        Returns:
            tuple: (успех операции (bool), сообщение об ошибке (str))
        """
        try:
            if not query or not query.strip():
                self.logger.warning("Попытка выполнить пустой запрос")
                return False, "Пустой запрос"

            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            self.connection.commit()
            self.logger.info(f"Выполнен UPDATE/DDL запрос: {self.cursor.rowcount} строк затронуто")
            return True, ""
        except psycopg2.Error as e:
            self.connection.rollback()
            error_msg = str(e)
            self.logger.error(f"Ошибка выполнения UPDATE/DDL запроса: {error_msg}")
            return False, error_msg

    def create_table(self, table_name, columns):
        """
        Создание новой таблицы.

        Args:
            table_name: Имя таблицы
            columns: Список словарей [{'name': 'col1', 'type': 'INTEGER'}, ...]

        Returns:
            tuple: (успех операции (bool), сообщение об ошибке (str))
        """
        try:
            column_definitions = []
            for col in columns:
                column_definitions.append(f"{sql.Identifier(col['name']).as_string(self.cursor)} {col['type']}")

            query = f"CREATE TABLE {sql.Identifier(table_name).as_string(self.cursor)} ({', '.join(column_definitions)})"
            self.cursor.execute(query)
            self.connection.commit()
            self.logger.info(f"Создана таблица {table_name}")
            return True, ""
        except psycopg2.Error as e:
            self.connection.rollback()
            error_msg = str(e)
            self.logger.error(f"Ошибка создания таблицы {table_name}: {error_msg}")
            return False, error_msg

    def drop_table(self, table_name):
        """
        Удаление таблицы.

        Args:
            table_name: Имя таблицы

        Returns:
            tuple: (успех операции (bool), сообщение об ошибке (str))
        """
        try:
            query = f"DROP TABLE IF EXISTS {sql.Identifier(table_name).as_string(self.cursor)} CASCADE"
            self.cursor.execute(query)
            self.connection.commit()
            self.logger.info(f"Удалена таблица {table_name}")
            return True, ""
        except psycopg2.Error as e:
            self.connection.rollback()
            error_msg = str(e)
            self.logger.error(f"Ошибка удаления таблицы {table_name}: {error_msg}")
            return False, error_msg

    def get_table_data(self, table_name, columns=None, where=None, order_by=None, group_by=None, having=None,
                       params=None):
        """
        Получение данных из таблицы с возможностью фильтрации и сортировки.

        Args:
            table_name: Имя таблицы
            columns: Список столбцов для выборки (None = все)
            where: Условие WHERE
            order_by: Условие ORDER BY
            group_by: Условие GROUP BY
            having: Условие HAVING
            params: Параметры для WHERE

        Returns:
            list: Результаты запроса
        """
        try:
            cols = ', '.join(columns) if columns else '*'

            table_identifier = sql.Identifier(table_name)
            query = f"SELECT {cols} FROM {table_identifier.as_string(self.cursor)}"

            if where:
                query += f" WHERE {where}"
            if group_by:
                query += f" GROUP BY {group_by}"
            if having:
                query += f" HAVING {having}"
            if order_by:
                query += f" ORDER BY {order_by}"

            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)

            return self.cursor.fetchall()
        except psycopg2.Error as e:
            self.logger.error(f"Ошибка получения данных таблицы {table_name}: {str(e)}")
            self.connection.rollback()
            return []

    def add_table_column(self, table_name, column_name, data_type, nullable=True, default=None):
        """
        Добавление нового столбца в таблицу.

        Args:
            table_name: Имя таблицы
            column_name: Имя столбца
            data_type: Тип данных
            nullable: Может ли быть NULL
            default: Значение по умолчанию

        Returns:
            tuple: (успех операции (bool), сообщение об ошибке (str))
        """
        try:
            query = f"ALTER TABLE {sql.Identifier(table_name).as_string(self.cursor)} ADD COLUMN {sql.Identifier(column_name).as_string(self.cursor)} {data_type}"

            if not nullable:
                if default is not None:
                    query += f" DEFAULT {default}"
                query += " NOT NULL"
            elif default is not None:
                query += f" DEFAULT {default}"

            self.cursor.execute(query)
            self.connection.commit()
            self.logger.info(f"Добавлен столбец {column_name} в таблицу {table_name}")
            return True, ""
        except psycopg2.Error as e:
            self.connection.rollback()
            error_msg = str(e)
            self.logger.error(f"Ошибка добавления столбца: {error_msg}")
            return False, error_msg

    def drop_table_column(self, table_name, column_name):
        """
        Удаление столбца из таблицы.

        Args:
            table_name: Имя таблицы
            column_name: Имя столбца

        Returns:
            tuple: (успех операции (bool), сообщение об ошибке (str))
        """
        try:
            query = f"ALTER TABLE {sql.Identifier(table_name).as_string(self.cursor)} DROP COLUMN {sql.Identifier(column_name).as_string(self.cursor)}"
            self.cursor.execute(query)
            self.connection.commit()
            self.logger.info(f"Удален столбец {column_name} из таблицы {table_name}")
            return True, ""
        except psycopg2.Error as e:
            self.connection.rollback()
            error_msg = str(e)
            self.logger.error(f"Ошибка удаления столбца: {error_msg}")
            return False, error_msg

    def rename_table_column(self, table_name, old_name, new_name):
        """
        Переименование столбца таблицы.

        Args:
            table_name: Имя таблицы
            old_name: Старое имя столбца
            new_name: Новое имя столбца

        Returns:
            tuple: (успех операции (bool), сообщение об ошибке (str))
        """
        try:
            query = (
                f"ALTER TABLE {sql.Identifier(table_name).as_string(self.cursor)} "
                f"RENAME COLUMN {sql.Identifier(old_name).as_string(self.cursor)} "
                f"TO {sql.Identifier(new_name).as_string(self.cursor)}"
            )
            self.cursor.execute(query)
            self.connection.commit()
            self.logger.info(f"Переименован столбец {old_name} -> {new_name} в таблице {table_name}")
            return True, ""
        except psycopg2.Error as e:
            self.connection.rollback()
            error_msg = str(e)
            self.logger.error(f"Ошибка переименования столбца: {error_msg}")
            return False, error_msg

    def rename_table(self, old_name, new_name):
        """
        Переименование таблицы.

        Args:
            old_name: Старое имя таблицы
            new_name: Новое имя таблицы

        Returns:
            tuple: (успех операции (bool), сообщение об ошибке (str))
        """
        try:
            query = f"ALTER TABLE {sql.Identifier(old_name).as_string(self.cursor)} RENAME TO {sql.Identifier(new_name).as_string(self.cursor)}"
            self.cursor.execute(query)
            self.connection.commit()
            self.logger.info(f"Переименована таблица {old_name} -> {new_name}")
            return True, ""
        except psycopg2.Error as e:
            self.connection.rollback()
            error_msg = str(e)
            self.logger.error(f"Ошибка переименования таблицы: {error_msg}")
            return False, error_msg

    def alter_column_type(self, table_name, column_name, new_type):
        """
        Изменение типа данных столбца.

        Args:
            table_name: Имя таблицы
            column_name: Имя столбца
            new_type: Новый тип данных

        Returns:
            tuple: (успех операции (bool), сообщение об ошибке (str))
        """
        try:
            query = f"ALTER TABLE {sql.Identifier(table_name).as_string(self.cursor)} ALTER COLUMN {sql.Identifier(column_name).as_string(self.cursor)} TYPE {new_type}"
            self.cursor.execute(query)
            self.connection.commit()
            self.logger.info(f"Изменен тип столбца {column_name} в таблице {table_name} на {new_type}")
            return True, ""
        except psycopg2.Error as e:
            self.connection.rollback()
            error_msg = str(e)
            self.logger.error(f"Ошибка изменения типа столбца: {error_msg}")
            return False, error_msg

    def set_column_constraint(self, table_name, column_name, constraint_type, constraint_value=None):
        """
        Установка ограничения на столбец.

        Args:
            table_name: Имя таблицы
            column_name: Имя столбца
            constraint_type: Тип ограничения (NOT NULL, UNIQUE, CHECK, FOREIGN KEY)
            constraint_value:
                - для CHECK: строка с условием CHECK
                - для FOREIGN KEY: кортеж (ref_table, ref_column)

        Returns:
            tuple: (успех (bool), сообщение об ошибке (str))
        """
        try:
            if constraint_type == 'NOT NULL':
                query = (
                    f"ALTER TABLE {sql.Identifier(table_name).as_string(self.cursor)} "
                    f"ALTER COLUMN {sql.Identifier(column_name).as_string(self.cursor)} SET NOT NULL"
                )
            elif constraint_type == 'UNIQUE':
                query = (
                    f"ALTER TABLE {sql.Identifier(table_name).as_string(self.cursor)} "
                    f"ADD UNIQUE ({sql.Identifier(column_name).as_string(self.cursor)})"
                )
            elif constraint_type == 'CHECK' and constraint_value:
                constraint_name = f"{table_name}_{column_name}_check"
                query = (
                    f"ALTER TABLE {sql.Identifier(table_name).as_string(self.cursor)} "
                    f"ADD CONSTRAINT {sql.Identifier(constraint_name).as_string(self.cursor)} "
                    f"CHECK ({constraint_value})"
                )
            elif constraint_type == 'FOREIGN KEY' and isinstance(constraint_value, tuple) and len(constraint_value) == 2:
                ref_table, ref_column = constraint_value
                constraint_name = f"{table_name}_{column_name}_fk"
                query = (
                    f"ALTER TABLE {sql.Identifier(table_name).as_string(self.cursor)} "
                    f"ADD CONSTRAINT {sql.Identifier(constraint_name).as_string(self.cursor)} "
                    f"FOREIGN KEY ({sql.Identifier(column_name).as_string(self.cursor)}) "
                    f"REFERENCES {sql.Identifier(ref_table).as_string(self.cursor)} "
                    f"({sql.Identifier(ref_column).as_string(self.cursor)})"
                )
            else:
                return False, "Неизвестный тип ограничения или неверные параметры"

            self.cursor.execute(query)
            self.connection.commit()
            self.logger.info(
                f"Установлено ограничение {constraint_type} на столбец {column_name} в таблице {table_name}"
            )
            return True, ""
        except psycopg2.Error as e:
            self.connection.rollback()
            error_msg = str(e)
            self.logger.error(f"Ошибка установки ограничения: {error_msg}")
            return False, error_msg

    def drop_column_constraint(self, table_name, column_name, constraint_type):
        """
        Снятие ограничения со столбца.

        Args:
            table_name: Имя таблицы
            column_name: Имя столбца
            constraint_type: Тип ограничения (NOT NULL, UNIQUE, CHECK, FOREIGN KEY)

        Returns:
            tuple: (успех операции (bool), сообщение об ошибке (str))
        """
        try:
            if constraint_type == 'NOT NULL':
                query = (
                    f"ALTER TABLE {sql.Identifier(table_name).as_string(self.cursor)} "
                    f"ALTER COLUMN {sql.Identifier(column_name).as_string(self.cursor)} DROP NOT NULL"
                )
                self.cursor.execute(query)
            elif constraint_type in ('UNIQUE', 'CHECK', 'FOREIGN KEY'):
                # Ищем имя ограничения для конкретного столбца
                # Для FOREIGN KEY используем key_column_usage, для UNIQUE/CHECK тоже можно связать по колонке
                self.cursor.execute("""
                    SELECT tc.constraint_name, tc.constraint_type
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                      ON tc.constraint_name = kcu.constraint_name
                     AND tc.table_schema = kcu.table_schema
                     AND tc.table_name = kcu.table_name
                    WHERE tc.table_schema = 'public'
                      AND tc.table_name = %s
                      AND kcu.column_name = %s
                      AND tc.constraint_type = %s
                    UNION ALL
                    SELECT tc.constraint_name, tc.constraint_type
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.constraint_column_usage ccu
                      ON tc.constraint_name = ccu.constraint_name
                     AND tc.table_schema = ccu.table_schema
                     AND tc.table_name = ccu.table_name
                    WHERE tc.table_schema = 'public'
                      AND tc.table_name = %s
                      AND ccu.column_name = %s
                      AND tc.constraint_type = %s
                    LIMIT 1
                """, (table_name, column_name, constraint_type,
                      table_name, column_name, constraint_type))
                row = self.cursor.fetchone()
                if not row:
                    return False, "Ограничение для указанного столбца не найдено"
                constraint_name = row[0]

                drop_q = (
                    f"ALTER TABLE {sql.Identifier(table_name).as_string(self.cursor)} "
                    f"DROP CONSTRAINT {sql.Identifier(constraint_name).as_string(self.cursor)}"
                )
                self.cursor.execute(drop_q)
            else:
                return False, "Неизвестный тип ограничения"

            self.connection.commit()
            self.logger.info(f"Снято ограничение {constraint_type} со столбца {column_name} в таблице {table_name}")
            return True, ""
        except psycopg2.Error as e:
            self.connection.rollback()
            error_msg = str(e)
            self.logger.error(f"Ошибка снятия ограничения: {error_msg}")
            return False, error_msg

    def insert_table_row(self, table_name, data):
        """
        Вставка новой записи в таблицу.

        Args:
            table_name: Имя таблицы
            data: Словарь {имя_столбца: значение}

        Returns:
            tuple: (успех операции (bool), сообщение об ошибке (str))
        """
        try:
            columns = list(data.keys())
            values = list(data.values())

            cols_str = ', '.join([sql.Identifier(col).as_string(self.cursor) for col in columns])
            placeholders = ', '.join(['%s'] * len(values))

            query = f"INSERT INTO {sql.Identifier(table_name).as_string(self.cursor)} ({cols_str}) VALUES ({placeholders})"
            self.cursor.execute(query, values)
            self.connection.commit()
            self.logger.info(f"Добавлена запись в таблицу {table_name}")
            return True, ""
        except psycopg2.Error as e:
            self.connection.rollback()
            error_msg = str(e)
            self.logger.error(f"Ошибка добавления записи: {error_msg}")
            return False, error_msg

    def update_table_row(self, table_name, data, where_clause, where_params):
        """
        Обновление записи в таблице.

        Args:
            table_name: Имя таблицы
            data: Словарь {имя_столбца: новое_значение}
            where_clause: Условие WHERE
            where_params: Параметры для WHERE

        Returns:
            tuple: (успех операции (bool), сообщение об ошибке (str))
        """
        try:
            set_parts = [f"{sql.Identifier(col).as_string(self.cursor)} = %s" for col in data.keys()]
            set_clause = ', '.join(set_parts)

            query = f"UPDATE {sql.Identifier(table_name).as_string(self.cursor)} SET {set_clause} WHERE {where_clause}"
            params = list(data.values()) + list(where_params)

            self.cursor.execute(query, params)
            self.connection.commit()
            self.logger.info(f"Обновлена запись в таблице {table_name}")
            return True, ""
        except psycopg2.Error as e:
            self.connection.rollback()
            error_msg = str(e)
            self.logger.error(f"Ошибка обновления записи: {error_msg}")
            return False, error_msg

    def delete_table_row(self, table_name, where_clause, where_params):
        """
        Удаление записи из таблицы.

        Args:
            table_name: Имя таблицы
            where_clause: Условие WHERE
            where_params: Параметры для WHERE

        Returns:
            tuple: (успех операции (bool), сообщение об ошибке (str))
        """
        try:
            query = f"DELETE FROM {sql.Identifier(table_name).as_string(self.cursor)} WHERE {where_clause}"
            self.cursor.execute(query, where_params)
            self.connection.commit()
            self.logger.info(f"Удалена запись из таблицы {table_name}")
            return True, ""
        except psycopg2.Error as e:
            self.connection.rollback()
            error_msg = str(e)
            self.logger.error(f"Ошибка удаления записи: {error_msg}")
            return False, error_msg

    def execute_join_query(self, tables_info, selected_columns, join_conditions, where=None, order_by=None,
                           group_by=None, having=None):
        """
        Выполнение JOIN запроса.

        Args:
            tables_info: Список словарей [{name: имя_таблицы, alias: алиас}]
            selected_columns: Список столбцов для выборки ["table.column", ...]
            join_conditions: Список условий JOIN [{type: 'INNER', table: 'table2', on: 'table1.id = table2.id'}]
            where: Условие WHERE
            order_by: Условие ORDER BY
            group_by: Условие GROUP BY
            having: Условие HAVING

        Returns:
            list: Результаты запроса
        """
        try:
            cols = ', '.join(selected_columns) if selected_columns else '*'

            main_table = tables_info[0]
            query = f"SELECT {cols} FROM {main_table['name']}"
            if main_table.get('alias'):
                query += f" AS {main_table['alias']}"

            for join in join_conditions:
                query += f" {join['type']} JOIN {join['table']}"
                if join.get('alias'):
                    query += f" AS {join['alias']}"
                query += f" ON {join['on']}"

            if where:
                query += f" WHERE {where}"
            if group_by:
                query += f" GROUP BY {group_by}"
            if having:
                query += f" HAVING {having}"
            if order_by:
                query += f" ORDER BY {order_by}"

            self.logger.info(f"Выполнение JOIN запроса: {query}")
            self.cursor.execute(query)

            result = self.cursor.fetchall()
            self.logger.info(f"Получено {len(result)} записей из JOIN запроса")
            return result

        except psycopg2.Error as e:
            self.logger.error(f"Ошибка выполнения JOIN запроса: {str(e)}")
            self.connection.rollback()
            return []

    def list_enum_types(self):
        """
        Получение списка пользовательских ENUM типов (public schema).
        """
        try:
            self.cursor.execute("""
                SELECT typname
                FROM pg_type
                WHERE typtype = 'e'
                  AND typnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
                ORDER BY typname
            """)
            return [r[0] for r in self.cursor.fetchall()]
        except psycopg2.Error as e:
            self.logger.error(f"Ошибка получения ENUM типов: {str(e)}")
            self.connection.rollback()
            return []

    def list_composite_types(self):
        """
        Получение списка составных типов, исключая типы таблиц (row types).
        """
        try:
            self.cursor.execute("""
                SELECT t.typname
                FROM pg_type t
                WHERE t.typtype = 'c'
                  AND t.typnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
                  AND NOT EXISTS (
                    SELECT 1 FROM pg_class c WHERE c.reltype = t.oid
                  )
                ORDER BY t.typname
            """)
            return [r[0] for r in self.cursor.fetchall()]
        except psycopg2.Error as e:
            self.logger.error(f"Ошибка получения составных типов: {str(e)}")
            self.connection.rollback()
            return []

    def create_enum_type(self, type_name, values):
        """
        Создание ENUM типа.
        values: список строк.
        """
        try:
            if not values:
                return False, "Список значений пуст"
            escaped = ", ".join([f"'{v}'" for v in values])
            q = f"CREATE TYPE {sql.Identifier(type_name).as_string(self.cursor)} AS ENUM ({escaped})"
            self.cursor.execute(q)
            self.connection.commit()
            self.logger.info(f"Создан ENUM тип {type_name}")
            return True, ""
        except psycopg2.Error as e:
            self.connection.rollback()
            return False, str(e)

    def create_composite_type(self, type_name, columns):
        """
        Создание составного типа.
        columns: список кортежей (name, type)
        """
        try:
            if not columns:
                return False, "Нет столбцов"
            col_defs = []
            for cname, ctype in columns:
                col_defs.append(f"{sql.Identifier(cname).as_string(self.cursor)} {ctype}")
            q = f"CREATE TYPE {sql.Identifier(type_name).as_string(self.cursor)} AS ({', '.join(col_defs)})"
            self.cursor.execute(q)
            self.connection.commit()
            self.logger.info(f"Создан составной тип {type_name}")
            return True, ""
        except psycopg2.Error as e:
            self.connection.rollback()
            return False, str(e)

    def drop_type(self, type_name):
        """
        Удаление пользовательского типа (ENUM или составного).
        """
        try:
            q = f"DROP TYPE IF EXISTS {sql.Identifier(type_name).as_string(self.cursor)} CASCADE"
            self.cursor.execute(q)
            self.connection.commit()
            self.logger.info(f"Удалён тип {type_name}")
            return True, ""
        except psycopg2.Error as e:
            self.connection.rollback()
            return False, str(e)

    def list_enum_types(self):
        try:
            self.cursor.execute("""
                SELECT typname
                FROM pg_type
                WHERE typtype = 'e'
                  AND typnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
                ORDER BY typname
            """)
            return [r[0] for r in self.cursor.fetchall()]
        except psycopg2.Error as e:
            self.logger.error(f"Ошибка получения ENUM типов: {str(e)}")
            self.connection.rollback()
            return []

    def list_enum_values(self, type_name):
        try:
            self.cursor.execute("""
                SELECT e.enumlabel
                FROM pg_type t
                JOIN pg_enum e ON e.enumtypid = t.oid
                WHERE t.typname = %s
                ORDER BY e.enumsortorder
            """, (type_name,))
            return [r[0] for r in self.cursor.fetchall()]
        except psycopg2.Error as e:
            self.logger.error(f"Ошибка получения значений ENUM {type_name}: {str(e)}")
            self.connection.rollback()
            return []

    def create_enum_type(self, type_name, values):
        try:
            if not values:
                return False, "Список значений пуст"
            escaped = ", ".join([self.cursor.mogrify("%s", (v,)).decode("utf-8") for v in values])
            q = f"CREATE TYPE {sql.Identifier(type_name).as_string(self.cursor)} AS ENUM ({escaped})"
            self.cursor.execute(q)
            self.connection.commit()
            self.logger.info(f"Создан ENUM тип {type_name}")
            return True, ""
        except psycopg2.Error as e:
            self.connection.rollback()
            return False, str(e)

    def add_enum_value(self, type_name, new_value, position=None, ref_value=None):
        """
        position: None | 'BEFORE' | 'AFTER'
        ref_value: строка опорного значения для BEFORE/AFTER
        """
        try:
            base = f"ALTER TYPE {sql.Identifier(type_name).as_string(self.cursor)} ADD VALUE "
            if position in ("BEFORE", "AFTER") and ref_value:
                q = base + f"%s {position} %s"
                self.cursor.execute(q, (new_value, ref_value))
            else:
                q = base + "%s"
                self.cursor.execute(q, (new_value,))
            self.connection.commit()
            self.logger.info(f"В ENUM {type_name} добавлено значение {new_value}")
            return True, ""
        except psycopg2.Error as e:
            self.connection.rollback()
            return False, str(e)

    def rename_enum_value(self, type_name, old_value, new_value):
        try:
            q = f"ALTER TYPE {sql.Identifier(type_name).as_string(self.cursor)} RENAME VALUE %s TO %s"
            self.cursor.execute(q, (old_value, new_value))
            self.connection.commit()
            self.logger.info(f"ENUM {type_name}: {old_value} -> {new_value}")
            return True, ""
        except psycopg2.Error as e:
            self.connection.rollback()
            return False, str(e)

    def drop_type(self, type_name):
        try:
            q = f"DROP TYPE IF EXISTS {sql.Identifier(type_name).as_string(self.cursor)} CASCADE"
            self.cursor.execute(q)
            self.connection.commit()
            self.logger.info(f"Удалён тип {type_name}")
            return True, ""
        except psycopg2.Error as e:
            self.connection.rollback()
            return False, str(e)

    # ---------- COMPOSITE ----------
    def list_composite_types(self):
        try:
            self.cursor.execute("""
                SELECT t.typname
                FROM pg_type t
                WHERE t.typtype = 'c'
                  AND t.typnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
                  AND NOT EXISTS (SELECT 1 FROM pg_class c WHERE c.reltype = t.oid)
                ORDER BY t.typname
            """)
            return [r[0] for r in self.cursor.fetchall()]
        except psycopg2.Error as e:
            self.logger.error(f"Ошибка получения составных типов: {str(e)}")
            self.connection.rollback()
            return []

    def list_composite_attributes(self, type_name):
        try:
            self.cursor.execute("""
                SELECT a.attname, pg_catalog.format_type(a.atttypid, a.atttypmod)
                FROM pg_type t
                JOIN pg_class c ON c.oid = t.typrelid
                JOIN pg_attribute a ON a.attrelid = c.oid
                WHERE t.typname = %s AND a.attnum > 0 AND NOT a.attisdropped
                ORDER BY a.attnum
            """, (type_name,))
            return [(r[0], r[1]) for r in self.cursor.fetchall()]
        except psycopg2.Error as e:
            self.logger.error(f"Ошибка получения атрибутов составного типа {type_name}: {str(e)}")
            self.connection.rollback()
            return []

    def create_composite_type(self, type_name, columns):
        try:
            if not columns:
                return False, "Нет столбцов"
            col_defs = []
            for cname, ctype in columns:
                col_defs.append(f"{sql.Identifier(cname).as_string(self.cursor)} {ctype}")
            q = f"CREATE TYPE {sql.Identifier(type_name).as_string(self.cursor)} AS ({', '.join(col_defs)})"
            self.cursor.execute(q)
            self.connection.commit()
            self.logger.info(f"Создан составной тип {type_name}")
            return True, ""
        except psycopg2.Error as e:
            self.connection.rollback()
            return False, str(e)

    def composite_add_attribute(self, type_name, attr_name, data_type):
        try:
            q = (
                f"ALTER TYPE {sql.Identifier(type_name).as_string(self.cursor)} "
                f"ADD ATTRIBUTE {sql.Identifier(attr_name).as_string(self.cursor)} {data_type}"
            )
            self.cursor.execute(q)
            self.connection.commit()
            self.logger.info(f"{type_name}: добавлен атрибут {attr_name} {data_type}")
            return True, ""
        except psycopg2.Error as e:
            self.connection.rollback()
            return False, str(e)

    def composite_drop_attribute(self, type_name, attr_name):
        try:
            q = (
                f"ALTER TYPE {sql.Identifier(type_name).as_string(self.cursor)} "
                f"DROP ATTRIBUTE {sql.Identifier(attr_name).as_string(self.cursor)}"
            )
            self.cursor.execute(q)
            self.connection.commit()
            self.logger.info(f"{type_name}: удалён атрибут {attr_name}")
            return True, ""
        except psycopg2.Error as e:
            self.connection.rollback()
            return False, str(e)

    def composite_rename_attribute(self, type_name, old_name, new_name):
        try:
            q = (
                f"ALTER TYPE {sql.Identifier(type_name).as_string(self.cursor)} "
                f"RENAME ATTRIBUTE {sql.Identifier(old_name).as_string(self.cursor)} "
                f"TO {sql.Identifier(new_name).as_string(self.cursor)}"
            )
            self.cursor.execute(q)
            self.connection.commit()
            self.logger.info(f"{type_name}: переименован атрибут {old_name} -> {new_name}")
            return True, ""
        except psycopg2.Error as e:
            self.connection.rollback()
            return False, str(e)

    def composite_alter_attribute_type(self, type_name, attr_name, new_type):
        try:
            q = (
                f"ALTER TYPE {sql.Identifier(type_name).as_string(self.cursor)} "
                f"ALTER ATTRIBUTE {sql.Identifier(attr_name).as_string(self.cursor)} "
                f"TYPE {new_type}"
            )
            self.cursor.execute(q)
            self.connection.commit()
            self.logger.info(f"{type_name}: изменён тип атрибута {attr_name} -> {new_type}")
            return True, ""
        except psycopg2.Error as e:
            self.connection.rollback()
            return False, str(e)