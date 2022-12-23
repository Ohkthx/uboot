"""Database manager for Aliass."""
from typing import Optional

from .db_socket import DbSocket, clean_name

# 0: int  - id
# 1: int  - guild_id
# 2: int  - msg_id
# 3: str  - name
# 4: int  - owner_id
AliasRaw = tuple[int, int, int, str, int]


class AliasDb(DbSocket):
    """Database manager for Aliases."""

    def __init__(self, filename: str) -> None:
        super().__init__(filename)
        self.table_name = clean_name('aliases')
        self.query['create_table'] = "CREATE TABLE IF NOT EXISTS {table_name} "\
            "( id INTEGER DESC, guild_id INTEGER, "\
            "msg_id INTEGER, "\
            "name TEXT, owner_id INTEGER )"
        self.query['find_one'] = "SELECT * FROM {table_name} WHERE "\
            "{condition}"
        self.query['insert_one'] = "INSERT OR IGNORE INTO {table_name} "\
            "VALUES(?, ?, ?, ?, ?)"

    def find_one(self, alias_id: int,
                 guild_id: int) -> Optional[AliasRaw]:
        """Gets a single alias from database based on its id."""
        where_key = f"id = {alias_id} AND guild_id = {guild_id}"
        return self._find_one(where_key)

    def find_last(self, guild_id: int) -> Optional[AliasRaw]:
        """Gets the last alias created for the guild."""
        where_key = f"guild_id = {guild_id} ORDER BY id DESC"
        return self._find_one(where_key)

    def find_all(self) -> list[AliasRaw]:
        """Pulls all aliases from databases. Optional to only pull
        disabled or enabled.
        """
        return self._find_many()

    def insert_one(self, raw: AliasRaw) -> None:
        """Adds one alias to the database only if it does not exist."""
        self._insert_one(raw)

    def update(self, raw: AliasRaw) -> None:
        """Updates an alias in the database, if it does not exist it will
        be created.
        """
        old = self.find_one(raw[0], raw[1])
        if not old:
            return self.insert_one(raw)

        # Update it here.
        set_key = f"msg_id = {raw[2]}, "\
            f"name = {raw[3]}, "\
            f"owner_id = {raw[4]}"
        where_key = f"id = {raw[0]} AND guild_id = {raw[1]}"
        self._update(set_key, where_key)
        return None

    def delete_one(self, raw: AliasRaw) -> None:
        """Removes a pair from database."""
        wherekey = f"id = {raw[0]} AND guild_id = {raw[1]}"
        self._delete(wherekey)
