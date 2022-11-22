from typing import Optional
from .db_socket import DbSocket

from user import User


class UserDb(DbSocket):
    def __init__(self, filename: str) -> None:
        super().__init__(filename)
        self.query['create_table'] = "CREATE TABLE IF NOT EXISTS [{table_name}] "\
            "( id INTEGER PRIMARY KEY DESC, "\
            "gold INTEGER, msg_count INTEGER)"
        self.query['save_many'] = "INSERT OR IGNORE INTO [{table_name}] "\
            "VALUES(?, ?, ?)"
        self.query['delete'] = "DELETE FROM {table_name} WHERE "\
            "{condition}"
        self.query['load_many'] = "SELECT * FROM [{table_name}]"

    def save_many(self, users: list[User]) -> None:
        if len(users) == 0:
            return
        items = list(map(lambda u: [u.id, u.gold, u.msg_count], users))
        self._save_many("user", items)

    def load_many(self) -> list[User]:
        raw_users = self._load_many("user", "")
        return [User(u[0], u[1], u[2]) for u in raw_users]
