"""Database manager for Log settings."""
from typing import Optional

from .db_socket import DbSocket, clean_name

# 0 : int - guild_id
# 1 : int - user_id
# 2 : int - type
# 3 : str - timestamp
# 4 : str - message
LogRaw = tuple[int, int, int, str, str]


class LogDb(DbSocket):
    """Database manager for logs."""

    def __init__(self, filename: str) -> None:
        super().__init__(filename)
        self.table_name = clean_name('logs')
        self.query['create_table'] = "CREATE TABLE IF NOT EXISTS {table_name} "\
            "( guild_id INTEGER, "\
            "user_id INTEGER, type INTEGER, "\
            "timestamp TEXT, message TEXT )"
        self.query['insert_one'] = "INSERT OR IGNORE INTO {table_name} "\
            "VALUES(?, ?, ?, ?, ?)"
        self.query['find_many'] = "SELECT * FROM {table_name} WHERE "

    def find_guild_type(self, guild_id: int, logtype: int) -> list[LogRaw]:
        """Finds guild logs based on type."""
        where_key = f"guild_id = {guild_id} AND type = {logtype}"
        return self._find_many(where_key)

    def find_guild_user(self, guild_id: int, user_id: int) -> list[LogRaw]:
        """Finds guild logs based on a user id."""
        where_key = f"guild_id = {guild_id} AND user_id = {user_id}"
        return self._find_many(where_key)

    def find_one(self, guild_id: int) -> Optional[LogRaw]:
        """Gets a single log based on its guild id."""
        where_key = f"guild_id = {guild_id}"
        return self._find_one(where_key)

    def insert_one(self, raw: LogRaw) -> None:
        """Adds one log to the database only if it does not exist."""
        self._insert_one(raw)
