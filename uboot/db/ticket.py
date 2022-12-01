from typing import Optional
from .db_socket import DbSocket

from managers import tickets


class TicketDb(DbSocket):
    def __init__(self, filename: str) -> None:
        super().__init__(filename)
        self.query['create_table'] = "CREATE TABLE IF NOT EXISTS {table_name} "\
            "( guild_id INTEGER DESC, id INTEGER, "\
            "title TEXT, done INTEGER DEFAULT 0 )"
        self.query['save_one'] = "INSERT OR IGNORE INTO {table_name} "\
            "VALUES(?, ?, ?, ?)"
        self.query['save_many'] = "INSERT OR IGNORE INTO {table_name} "\
            "VALUES(?, ?, ?, ?)"
        self.query['insert'] = "INSERT INTO {table_name} "\
            "VALUES ({value_key}) ON CONFLICT(guild_id, id) "\
            "DO UPDATE SET {set_key}"
        self.query['update'] = "UPDATE {table_name} SET {set_key} "\
            "WHERE {where_key}"
        self.query['delete'] = "DELETE FROM {table_name} WHERE "\
            "{condition}"
        self.query['load_one'] = "SELECT * FROM {table_name} WHERE "\
            "{condition}"
        self.query['load_many'] = "SELECT * FROM {table_name}"

    def save_many(self, all_tickets: list[tickets.Ticket]) -> None:
        if len(all_tickets) == 0:
            return
        items = list(map(lambda t: t._raw, all_tickets))
        self._save_many("ticket", items)

    def update(self, ticket: tickets.Ticket) -> None:
        old = self.load_one(ticket.guild_id, ticket.id)
        if not old:
            return self.save_one(ticket)

        # Update it here.
        set_key = f"done = {ticket.done}"
        where_key = f"guild_id = {ticket.guild_id} AND id = {ticket.id}"
        self._update("ticket", set_key, where_key)

    def save_one(self, ticket: tickets.Ticket) -> None:
        self._save_one("ticket", ticket._raw)

    def load_one(self, guild_id: int, id: int) -> Optional[tickets.Ticket]:
        where_key = f"guild_id = {guild_id} AND id = {id}"
        try:
            res = self._load_one("ticket", where_key)
            if res:
                return tickets.Ticket(res)
        except BaseException as err:
            print(f"ERROR IN L1: {err}")
        return None

    def load_many(self) -> list[tickets.Ticket]:
        raw_tickets = self._load_many("ticket", "")
        return [tickets.Manager.add(tickets.Ticket(t))
                for t in raw_tickets]
