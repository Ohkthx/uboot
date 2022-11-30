from typing import Optional
from .db_socket import DbSocket

from managers import tickets


class TicketDb(DbSocket):
    def __init__(self, filename: str) -> None:
        super().__init__(filename)
        self.query['create_table'] = "CREATE TABLE IF NOT EXISTS {table_name} "\
            "( id INTEGER PRIMARY KEY AUTOINCREMENT, "\
            "title TEXT, done INTEGER DEFAULT 0 )"
        self.query['save_many'] = "INSERT OR IGNORE INTO {table_name} "\
            "VALUES(?, ?, ?)"
        self.query['insert'] = "INSERT INTO {table_name} "\
            "VALUES ({value_key}) ON CONFLICT(id) "\
            "DO UPDATE SET {set_key}"
        self.query['delete'] = "DELETE FROM {table_name} WHERE "\
            "{condition}"
        self.query['load_many'] = "SELECT * FROM {table_name}"

    def save_many(self, all_tickets: list[tickets.Ticket]) -> None:
        if len(all_tickets) == 0:
            return
        items = list(map(lambda t: t._raw, all_tickets))
        self._save_many("ticket", items)

    def update(self, ticket: tickets.Ticket) -> None:
        t = ticket
        value_key = f"{t.id}, '{t.title}', {t.done}"
        set_key = f"title = '{t.title}', done = {t.done}"
        self._insert("ticket", value_key, set_key)

    def load_many(self) -> list[tickets.Ticket]:
        raw_tickets = self._load_many("ticket", "")
        return [tickets.Manager.add(tickets.Ticket(t))
                for t in raw_tickets]
