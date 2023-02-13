"""Database manager for Bank settings."""
from typing import Optional

from .db_socket import DbSocket, clean_name

# 0 : int - user_id
# 1 : str - inventory_id
# 2 : int - type
# 3 : int - capacity
# 4 : str - name
# 5 : str - parent_id
# 6 : str - items
InventoryRaw = tuple[int, str, int, int, str, str, str]


class InventoryDb(DbSocket):
    """Database manager for all inventories."""

    def __init__(self, filename: str) -> None:
        super().__init__(filename)
        self.table_name = clean_name('inventories')
        self.query['create_table'] = "CREATE TABLE IF NOT EXISTS {table_name} " \
                                     "( user_id INTEGER DESC, " \
                                     "inventory_id TEXT, "\
                                     "type INTEGER, "\
                                     "capacity INTEGER, "\
                                     "name TEXT, " \
                                     "parent_id TEXT, "\
                                     "items TEXT )"
        self.query['insert_one'] = "INSERT OR IGNORE INTO {table_name} " \
                                   "VALUES(?, ?, ?, ?, ?, ?, ?)"

    def find_one(self, inventory_id: str) -> Optional[InventoryRaw]:
        """Gets a single inventory based on its id."""
        where_key = f'inventory_id = "{inventory_id}"'
        return self._find_one(where_key)

    def find_all(self) -> list[InventoryRaw]:
        """Pulls all inventories from database."""
        return self._find_many()

    def insert_one(self, raw: InventoryRaw) -> None:
        """Adds one inventory to the database only if it does not exist."""
        self._insert_one(raw)

    def update(self, raw: InventoryRaw) -> None:
        """Updates an inventory in the database, if it does not exist it will
        be created.
        """
        old = self.find_one(raw[1])
        if not old:
            return self.insert_one(raw)

        # Update it here.
        set_key = f"type = {raw[2]}, " \
                  f"capacity = {raw[3]}, " \
                  f"name = {raw[4]}, " \
                  f"parent_id = {raw[5]}, " \
                  f"items = {raw[6]}"
        where_key = f'inventory_id = "{raw[1]}"'
        self._update(set_key, where_key)
        return None
