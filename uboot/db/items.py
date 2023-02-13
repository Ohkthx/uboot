"""Database manager for Bank settings."""
from typing import Optional

from .db_socket import DbSocket, clean_name

# 0 : str - id
# 1 : int - type
# 2 : str - name
# 3 : int - rarity
# 4 : int - material/reagent
# 5 : int - value
# 6 : int - uses
# 6 : int - uses_max
ItemRaw = tuple[str, int, str, int, int, int, int, int]


class ItemDb(DbSocket):
    """Database manager for all items."""

    def __init__(self, filename: str) -> None:
        super().__init__(filename)
        self.table_name = clean_name('items')
        self.query['create_table'] = "CREATE TABLE IF NOT EXISTS {table_name} " \
                                     "( item_id TEXT, " \
                                     "type INTEGER, "\
                                     "name TEXT, "\
                                     "rarity INTEGER, "\
                                     "material INTEGER, "\
                                     "value INTEGER, "\
                                     "uses INTEGER, "\
                                     "uses_max INTEGER )"
        self.query['insert_one'] = "INSERT OR IGNORE INTO {table_name} " \
                                   "VALUES(?, ?, ?, ?, ?, ?, ?, ?)"

    def find_one(self, item_id: str) -> Optional[ItemRaw]:
        """Gets a single item based on its id."""
        where_key = f'item_id = "{item_id}"'
        return self._find_one(where_key)

    def find_all(self) -> list[ItemRaw]:
        """Pulls all items from database."""
        return self._find_many()

    def insert_one(self, raw: ItemRaw) -> None:
        """Adds one item to the database only if it does not exist."""
        self._insert_one(raw)

    def update(self, raw: ItemRaw) -> None:
        """Updates an item in the database, if it does not exist it will
        be created.
        """
        old = self.find_one(raw[0])
        if not old:
            return self.insert_one(raw)

        # Update it here.
        set_key = f"type = {raw[1]}, " \
                  f"name = {raw[2]}, " \
                  f"rarity = {raw[3]}, " \
                  f"material = {raw[4]}, " \
                  f"value = {raw[5]}, " \
                  f"uses = {raw[6]}, " \
                  f"uses_max = {raw[7]}"
        where_key = f'item_id = "{raw[0]}"'
        self._update(set_key, where_key)
        return None

    def delete_one(self, raw: ItemRaw) -> None:
        """Removes an item from database."""
        where_key = f'item_id = "{raw[0]}"'
        self._delete(where_key)
