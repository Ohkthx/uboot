import sqlite3
from typing import Any, Optional


class DbSocket():

    @staticmethod
    def _clean_name(name: str) -> str:
        return ''.join(char for char in name if char.isalnum()).lower()

    def __init__(self, filename: str) -> None:
        if filename == "":
            raise ValueError("database filename cannot be empty.")
        self._is_saving: bool = False
        self._db_name = filename.lower()
        self._session = sqlite3.connect(filename)
        self._cursor = self._session.cursor()
        self._query = {
            'create_table': "",
            'save_many': "",
            'delete': "",
            'insert': "",
            'load_many': "",
            'table_exists': "SELECT name "
            "FROM sqlite_master "
            "WHERE name = '{table_name}'"
        }

    @property
    def db_name(self) -> str:
        return self._db_name

    @property
    def query(self) -> dict[str, str]:
        return self._query

    @property
    def is_saving(self) -> bool:
        return self._is_saving

    @query.setter
    def query(self, key: str, value: str):
        self._query[key] = value

    def _table_exists(self, table_name: str) -> bool:
        query = self.query['table_exists'].format(table_name=table_name)
        if self._cursor.execute(query).fetchone() is None:
            return False
        return True

    def _create_table(self, table_name: str) -> None:
        query = self.query['create_table'].format(table_name=table_name)
        self._cursor.execute(query)

    def _save_many(self, table_name: str, data) -> None:
        self._is_saving = True
        table_name = DbSocket._clean_name(table_name)
        self._create_table(table_name)

        query = self.query['save_many'].format(table_name=table_name)
        self._cursor.executemany(query, data)
        self._session.commit()
        self._is_saving = False

    def _insert(self, table_name: str, value_key: str, set_key: str) -> None:
        table_name = DbSocket._clean_name(table_name)
        self._create_table(table_name)

        query = self.query['insert'].format(table_name=table_name,
                                            value_key=value_key,
                                            set_key=set_key)
        try:
            res = self._cursor.execute(query)
        except BaseException as err:
            print(f"SQL EXCEPTION:\nQuery:\n{query}\n\n{err}")
        self._session.commit()

    def _delete(self, table_name: str, where_key: str) -> None:
        table_name = DbSocket._clean_name(table_name)
        if not self._table_exists(table_name):
            return

        query = self.query['delete'].format(table_name=table_name,
                                            condition=where_key)
        self._cursor.execute(query)
        self._session.commit()

    def _load_many(self,
                   table_name: str,
                   ext: Optional[str] = None) -> list[Any]:
        if ext is None:
            ext = ""
        table_name = DbSocket._clean_name(table_name)
        if not self._table_exists(table_name):
            return []

        query = self.query['load_many'].format(table_name=table_name)
        return self._cursor.execute(f"{query}{ext}").fetchall()
