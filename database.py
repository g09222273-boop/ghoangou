from pydantic import BaseModel

import sqlite3


def dict_factory(cursor, row) -> dict:
    save_dict = {}

    for idx, col in enumerate(cursor.description):
        save_dict[col[0]] = row[idx]

    return save_dict


def update_format(sql, parameters: dict) -> tuple[str, list]:
    values = ", ".join([
        f"{item} = ?" for item in parameters
    ])
    sql += f" {values}"

    return sql, list(parameters.values())


def update_format_where(sql, parameters: dict) -> tuple[str, list]:
    sql += " WHERE "

    sql += " AND ".join([
        f"{item} = ?" for item in parameters
    ])

    return sql, list(parameters.values())


class MessageRecord(BaseModel):
    user_id: int
    message_history: str



# Работа с юзером
class Messagesx:
    storage_name = "messages"
    PATH_DATABASE = "messages.db"

    @staticmethod
    def create_db():
        with sqlite3.connect('messages.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS messages
                              (id INTEGER PRIMARY KEY, user_id INTEGER, message_history TEXT)''')

    # Добавление записи
    @staticmethod
    def add(
            user_id: int,
            message_history: str,

    ):

        with sqlite3.connect(Messagesx.PATH_DATABASE) as con:
            con.row_factory = dict_factory

            con.execute(
                f"""
                    INSERT INTO {Messagesx.storage_name} (
                        user_id,
                        message_history
                    ) VALUES (?, ?)
                """,
                [
                    user_id,
                    message_history,
                ],
            )

    # Получение записи
    @staticmethod
    def get(**kwargs) -> MessageRecord:
        with sqlite3.connect(Messagesx.PATH_DATABASE) as con:
            con.row_factory = dict_factory
            sql = f"SELECT * FROM {Messagesx.storage_name}"
            sql, parameters = update_format_where(sql, kwargs)

            response = con.execute(sql, parameters).fetchone()

            if response is not None:
                response = MessageRecord(**response)

            return response

    # Получение записей
    @staticmethod
    def gets(**kwargs) -> list[MessageRecord]:
        with sqlite3.connect(Messagesx.PATH_DATABASE) as con:
            con.row_factory = dict_factory
            sql = f"SELECT * FROM {Messagesx.storage_name}"
            sql, parameters = update_format_where(sql, kwargs)

            response = con.execute(sql, parameters).fetchall()

            if len(response) >= 1:
                response = [MessageRecord(**cache_object) for cache_object in response]

            return response

    # Получение всех записей
    @staticmethod
    def get_all() -> list[MessageRecord]:
        with sqlite3.connect(Messagesx.PATH_DATABASE) as con:
            con.row_factory = dict_factory
            sql = f"SELECT * FROM {Messagesx.storage_name}"

            response = con.execute(sql).fetchall()

            if len(response) >= 1:
                response = [MessageRecord(**cache_object) for cache_object in response]

            return response

    # Редактирование записи
    @staticmethod
    def update(user_id, **kwargs):
        with sqlite3.connect(Messagesx.PATH_DATABASE) as con:
            con.row_factory = dict_factory
            sql = f"UPDATE {Messagesx.storage_name} SET"
            sql, parameters = update_format(sql, kwargs)
            parameters.append(user_id)

            con.execute(sql + "WHERE user_id = ?", parameters)

    # Удаление записи
    @staticmethod
    def delete(**kwargs):
        with sqlite3.connect(Messagesx.PATH_DATABASE) as con:
            con.row_factory = dict_factory
            sql = f"DELETE FROM {Messagesx.storage_name}"
            sql, parameters = update_format_where(sql, kwargs)

            con.execute(sql, parameters)

    # Очистка всех записей
    @staticmethod
    def clear():
        with sqlite3.connect(Messagesx.PATH_DATABASE) as con:
            con.row_factory = dict_factory
            sql = f"DELETE FROM {Messagesx.storage_name}"

            con.execute(sql)