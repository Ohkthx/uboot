from typing import Optional
from .db_socket import DbSocket

from managers import react_roles


class RoleDb(DbSocket):
    def __init__(self, filename: str) -> None:
        super().__init__(filename)
        self.query['create_table'] = "CREATE TABLE IF NOT EXISTS {table_name} "\
            "( role_id INTEGER PRIMARY KEY DESC, "\
            "guild_id INTEGER, reaction TEXT )"
        self.query['save_many'] = "INSERT OR IGNORE INTO {table_name} "\
            "VALUES(?, ?, ?)"
        self.query['insert'] = "INSERT INTO {table_name} "\
            "VALUES ({value_key}) ON CONFLICT(role_id) "\
            "DO UPDATE SET {set_key}"
        self.query['delete'] = "DELETE FROM {table_name} WHERE "\
            "{condition}"
        self.query['load_many'] = "SELECT * FROM {table_name}"

    def save_many(self, reacts: list[react_roles.ReactRole]) -> None:
        if len(reacts) == 0:
            return
        item = list(map(lambda r: r._raw, reacts))
        self._save_many("roles", item)

    def update(self, react_role: react_roles.ReactRole) -> None:
        r = react_role
        value_key = f"{r.role_id}, {r.guild_id}, '{r.reaction}'"
        set_key = f"reaction = '{r.reaction}'"
        self._insert("roles", value_key, set_key)

    def delete_one(self, react: react_roles.ReactRole) -> None:
        wherekey = f"guild_id = {react.guild_id} AND role_id = {react.role_id}"
        self._delete("roles", wherekey)

    def load_many(self) -> list[react_roles.ReactRole]:
        raw_reacts = self._load_many("roles", "")
        return [react_roles.Manager.add(
            react_roles.ReactRole(r)) for r in raw_reacts]
