"""Database manager for Support Tickets."""
from typing import Optional

from .db_socket import DbSocket, clean_name

# 0: int  - guild_id
# 1: int  - id
# 2: str  - title
# 3: bool - done
# 4: int  - owner_id
TicketRaw = tuple[int, int, str, bool, int]


class TicketDb(DbSocket):
    """Database manager for Support Tickets."""

    def __init__(self, filename: str) -> None:
        super().__init__(filename)
        self.table_name = clean_name('tickets')
        self.query['create_table'] = "CREATE TABLE IF NOT EXISTS {table_name} "\
            "( guild_id INTEGER DESC, id INTEGER, "\
            "title TEXT, done INTEGER DEFAULT 0, owner_id INTEGER )"
        self.query['find_one'] = "SELECT * FROM {table_name} WHERE "\
            "{condition}"
        self.query['insert_one'] = "INSERT OR IGNORE INTO {table_name} "\
            "VALUES(?, ?, ?, ?, ?)"

    def find_one(self, guild_id: int, ticket_id: int) -> Optional[TicketRaw]:
        """Gets a single ticket from database based on its id."""
        where_key = f"guild_id = {guild_id} AND id = {ticket_id}"
        return self._find_one(where_key)

    def find_last(self, guild_id: int) -> Optional[TicketRaw]:
        """Gets the most recent ticket created for a particular guild."""
        where_key = f"guild_id = {guild_id} ORDER BY id DESC"
        return self._find_one(where_key)

    def find_all(self, incomplete_only: bool = False) -> list[TicketRaw]:
        """Pulls all tickets from database."""
        ext = ''
        if incomplete_only:
            ext = ' WHERE done = 0'
        return self._find_many(ext)

    def insert_one(self, raw: TicketRaw) -> None:
        """Adds one ticket to the database only if it does not exist."""
        self._insert_one(raw)

    def update(self, raw: TicketRaw) -> None:
        """Updates a ticket in the database, if it does not exist it will
        be created.
        """
        old = self.find_one(raw[0], raw[1])
        if not old:
            return self.insert_one(raw)

        # Update it here.
        set_key = f"done = {raw[3]}"
        where_key = f"guild_id = {raw[0]} AND id = {raw[1]}"
        self._update(set_key, where_key)
        return None
