from typing import Optional
from .db_socket import DbSocket

from managers import users


class UserDb(DbSocket):
    def __init__(self, filename: str) -> None:
        super().__init__(filename)
        self.query['create_table'] = "CREATE TABLE IF NOT EXISTS [{table_name}] "\
            "( id INTEGER PRIMARY KEY DESC, "\
            "gold INTEGER, msg_count INTEGER, "\
            "gambles INTEGER, gambles_won INTEGER, "\
            "button_press INTEGER )"
        self.query['save_many'] = "INSERT OR IGNORE INTO [{table_name}] "\
            "VALUES(?, ?, ?, ?, ?, ?)"
        self.query['insert'] = "INSERT INTO {table_name} "\
            "VALUES ({value_key}) ON CONFLICT(id) "\
            "DO UPDATE SET {set_key}"
        self.query['delete'] = "DELETE FROM {table_name} WHERE "\
            "{condition}"
        self.query['load_many'] = "SELECT * FROM [{table_name}]"

    def save_many(self, users: list[users.User]) -> None:
        if len(users) == 0:
            return
        items = list(map(lambda u: u._raw, users))
        self._save_many("user", items)

    def update(self, user: users.User) -> None:
        u = user
        value_key = f"{u.id}, {u.gold}, {u.msg_count}, "\
            f"{u.gambles}, {u.gambles_won}, {u.button_press}"
        set_key = f"gold = {u.gold}, msg_count = {u.msg_count}, "\
            f"gambles = {u.gambles}, gambles_won = {u.gambles_won}, "\
            f"button_press = {u.button_press}"
        self._insert("user", value_key, set_key)

    def load_many(self) -> list[users.User]:
        raw_users = self._load_many("user", "")
        return [users.Manager.add(users.User(u)) for u in raw_users]
