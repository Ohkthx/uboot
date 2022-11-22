from typing import Optional
from .db_socket import DbSocket

from react_role import ReactRole


class RoleDb(DbSocket):
    def __init__(self, filename: str) -> None:
        super().__init__(filename)
        self.query['create_table'] = "CREATE TABLE IF NOT EXISTS [{table_name}] "\
            "( reaction TEXT PRIMARY KEY DESC, "\
            "role_id INTEGER, guild_id INTEGER)"
        self.query['save_many'] = "INSERT OR IGNORE INTO [{table_name}] "\
            "VALUES(?, ?, ?)"
        self.query['delete'] = "DELETE FROM {table_name} WHERE "\
            "{condition}"
        self.query['load_many'] = "SELECT * FROM [{table_name}]"

    def save_many(self, reacts: list[ReactRole]) -> None:
        if len(reacts) == 0:
            return
        item = list(map(lambda r: [r.reaction, r.role_id, r.guild_id], reacts))
        self._save_many("roles", item)

    def delete_one(self, react: ReactRole) -> None:
        wherekey = f"guild_id = {react.guild_id} AND role_id = {react.role_id}"
        self._delete("roles", wherekey)

    def load_many(self) -> list[ReactRole]:
        raw_reacts = self._load_many("roles", "")
        return [ReactRole(r[0], r[1], r[2]) for r in raw_reacts]
