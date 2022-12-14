"""The root of database access. Inherited for individual database managers."""
import os
import sqlite3
from typing import Any, Optional


def clean_name(name: str) -> str:
    """Cleans a table name so that is will not cause issues."""
    return ''.join(char for char in name if char.isalnum()
                   or char == '_').lower()


valid_keys = ('find_one', 'find_many', 'insert_one', 'insert_many', 'update',
              'delete', 'create_table', 'table_exists')


class DbSocket():
    """The root of database access. Inherited for individual database managers."""

    def __init__(self, filename: str) -> None:
        if filename == "":
            raise ValueError("database filename cannot be empty.")

        if not os.path.exists("dbs"):
            os.makedirs("dbs")

        self._is_saving: bool = False
        self._db_name = filename.lower()
        self._session = sqlite3.connect(f"dbs/{filename}")
        self._cursor = self._session.cursor()
        self.table_name = 'none'
        self._query = {
            'find_one': 'SELECT * FROM {table_name} WHERE {condition}',
            'find_many': 'SELECT * FROM {table_name}',
            'insert_one': '',
            'insert_many': '',
            'update': 'UPDATE {table_name} SET {set_key} WHERE '
            '{where_key}',
            'delete': 'DELETE FROM {table_name} WHERE {condition}',
            'create_table': '',
            'table_exists': "SELECT name "
            "FROM sqlite_master "
            "WHERE name = '{table_name}'"
        }

    @property
    def db_name(self) -> str:
        """Get the databases name."""
        return self._db_name

    @property
    def query(self) -> dict[str, str]:
        """Get the databases queries."""
        return self._query

    @query.setter
    def query(self, key: str, value: str):
        """Set a query in the database."""
        if key not in valid_keys:
            raise ValueError(f"invalid key '{key}' for '{self.table_name}'.")
        self._query[key] = value

    @property
    def is_saving(self) -> bool:
        """Checks if the database is currently saving."""
        return self._is_saving

    def _find_one(self, where_key: str) -> Optional[Any]:
        """Retrieve a single item from database, based on a WHERE clause."""
        if not self._table_exists(self.table_name):
            # If there is not a table, there are no items.
            return
        query = self.query['find_one'].format(table_name=self.table_name,
                                              condition=where_key)
        return self._cursor.execute(query).fetchone()

    def _find_many(self, ext: Optional[str] = None) -> list[Any]:
        """Retrieve several items from database."""
        if not ext:
            ext = ''
        if not self._table_exists(self.table_name):
            return []

        query = self.query['find_many'].format(table_name=self.table_name)
        res = self._cursor.execute(f"{query}{ext}").fetchall()
        return res if res else []

    def _insert_one(self, data) -> None:
        """Adds a single item to database, if it already exist then it is
        discarded.
        """
        self._is_saving = True
        self._create_table(self.table_name)

        query = self.query['insert_one'].format(table_name=self.table_name)
        try:
            self._cursor.execute(query, data)
            self._session.commit()
        except BaseException as err:
            print(f"SQL EXCEPTION:\nQuery:\n{query}\n\n{err}")
        finally:
            self._is_saving = False

    def _insert_many(self, data) -> None:
        """Adds serveral items to database, if they already exist then the
        individual one is ignored.
        """
        self._is_saving = True
        self._create_table(self.table_name)

        query = self.query['insert_many'].format(table_name=self.table_name)
        try:
            self._cursor.executemany(query, data)
            self._session.commit()
        except BaseException as err:
            print(f"SQL EXCEPTION:\nQuery:\n{query}\n\n{err}")
        finally:
            self._is_saving = False

    def _update(self, set_key: str, where_key: str) -> None:
        """Attempts to update an item in the database."""
        self._is_saving = True
        self._create_table(self.table_name)

        # Build the query.
        query = self.query['update'].format(table_name=self.table_name,
                                            set_key=set_key,
                                            where_key=where_key)
        try:
            self._cursor.execute(query)
            self._session.commit()
        except BaseException as err:
            print(f"SQL EXCEPTION:\nQuery:\n{query}\n\n{err}")
        finally:
            self._is_saving = False

    def _delete(self, where_key: str) -> None:
        """Removes a single item from a database based on a  WHERE clause."""
        if not self._table_exists(self.table_name):
            return

        # Build the query.
        query = self.query['delete'].format(table_name=self.table_name,
                                            condition=where_key)
        try:
            self._cursor.execute(query)
            self._session.commit()
        except BaseException as err:
            print(f"SQL EXCEPTION:\nQuery:\n{query}\n\n{err}")

    def _create_table(self, table_name: str) -> None:
        """Creates a table."""
        query = self.query['create_table'].format(table_name=table_name)
        self._cursor.execute(query)

    def _table_exists(self, table_name: str) -> bool:
        """Check if a table exists already."""
        query = self.query['table_exists'].format(table_name=table_name)
        if self._cursor.execute(query).fetchone() is None:
            return False
        return True
