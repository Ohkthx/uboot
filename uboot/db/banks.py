"""Database manager for Bank settings."""
from typing import Optional

from .db_socket import DbSocket, clean_name

# 0 : int - user_id
# 14: str - items
BankRaw = tuple[int, str]


class BankDb(DbSocket):
    """Database manager for Bank settings."""

    def __init__(self, filename: str) -> None:
        super().__init__(filename)
        self.table_name = clean_name('banks')
        self.query['create_table'] = "CREATE TABLE IF NOT EXISTS {table_name} "\
            "( user_id INTEGER PRIMARY KEY DESC, "\
            "items TEXT )"
        self.query['insert_one'] = "INSERT OR IGNORE INTO {table_name} "\
            "VALUES(?, ?)"

    def find_one(self, bank_id: int) -> Optional[BankRaw]:
        """Gets a single bank based on its id."""
        where_key = f"user_id = {bank_id}"
        return self._find_one(where_key)

    def find_all(self) -> list[BankRaw]:
        """Pulls all banks from database."""
        return self._find_many()

    def insert_one(self, raw: BankRaw) -> None:
        """Adds one bank to the database only if it does not exist."""
        self._insert_one(raw)

    def update(self, raw: BankRaw) -> None:
        """Updates a bank in the database, if it does not exist it will
        be created.
        """
        old = self.find_one(raw[0])
        if not old:
            return self.insert_one(raw)

        # Update it here.
        set_key = f"items = {raw[1]}"
        where_key = f"user_id = {raw[0]}"
        self._update(set_key, where_key)
        return None
