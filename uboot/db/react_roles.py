from typing import Optional
from .db_socket import DbSocket, clean_name

# 0: int  - role_id
# 1: int  - guild_id
# 2: str  - reaction
# 3: bool - reversed
ReactRoleRaw = tuple[int, int, str, bool]


class RoleDb(DbSocket):
    def __init__(self, filename: str) -> None:
        super().__init__(filename)
        self.table_name = clean_name('react_roles')
        self.query['create_table'] = "CREATE TABLE IF NOT EXISTS {table_name} "\
            "( role_id INTEGER PRIMARY KEY DESC, "\
            "guild_id INTEGER, reaction TEXT, reversed INTEGER )"
        self.query['insert_one'] = "INSERT OR IGNORE INTO {table_name} "\
            "VALUES (?, ?, ?, ?)"

    def find_one(self, role_id: int) -> Optional[ReactRoleRaw]:
        where_key = f"role_id = {role_id}"
        return self._find_one(where_key)

    def find_all(self) -> list[ReactRoleRaw]:
        return self._find_many()

    def insert_one(self, raw: ReactRoleRaw) -> None:
        self._insert_one(raw)

    def update(self, raw: ReactRoleRaw) -> None:
        old = self.find_one(raw[0])
        if not old:
            return self.insert_one(raw)

        set_key = f"reaction = {raw[2]}, reversed = {raw[3]}"
        where_key = f"role_id = {raw[0]}"
        self._update(set_key, where_key)

    def delete_one(self, raw: ReactRoleRaw) -> None:
        wherekey = f"role_id = {raw[0]} AND guild_id = {raw[1]}"
        self._delete(wherekey)
