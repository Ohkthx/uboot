from typing import Optional
from .db_socket import DbSocket, clean_name

# 0: int  - id
# 1: int  - guild_id
# 2: str  - name
# 3: int  - owner_id
# 4: int  - thread_id
# 5: int  - msg_id
# 6: bool - disabled
# 7: str  - banned
SubGuildRaw = tuple[int, int, str, int, int, int, bool, str]


class SubGuildDb(DbSocket):
    def __init__(self, filename: str) -> None:
        super().__init__(filename)
        self.table_name = clean_name('sub_guilds')
        self.query['create_table'] = "CREATE TABLE IF NOT EXISTS {table_name} "\
            "( id INTEGER DESC, guild_id INTEGER, name TEXT, owner_id INTEGER, "\
            "thread_id INTEGER, msg_id INTEGER, disabled INTEGER DEFAULT 0, "\
            "banned TEXT )"
        self.query['find_one'] = "SELECT * FROM {table_name} WHERE "\
            "{condition}"
        self.query['insert_one'] = "INSERT OR IGNORE INTO {table_name} "\
            "VALUES(?, ?, ?, ?, ?, ?, ?, ?)"

    def find_one(self, id: int, guild_id: int) -> Optional[SubGuildRaw]:
        where_key = f"id = {id} AND guild_id = {guild_id}"
        return self._find_one(where_key)

    def find_last(self, guild_id: int) -> Optional[SubGuildRaw]:
        where_key = f"guild_id = {guild_id} ORDER BY id DESC"
        return self._find_one(where_key)

    def find_all(self, incomplete_only: bool = False) -> list[SubGuildRaw]:
        ext = ''
        if incomplete_only:
            ext = ' WHERE disabled = 0'
        return self._find_many(ext)

    def insert_one(self, raw: SubGuildRaw) -> None:
        self._insert_one(raw)

    def update(self, raw: SubGuildRaw) -> None:
        old = self.find_one(raw[0], raw[1])
        if not old:
            return self.insert_one(raw)

        # Update it here.
        set_key = f"name = {raw[2]}, "\
            f"owner_id = {raw[3]}, "\
            f"thread_id = {raw[4]}, "\
            f"msg_id = {raw[5]}, "\
            f"disabled = {raw[6]}, "\
            f"banned = {raw[7]}"
        where_key = f"id = {raw[0]} AND guild_id = {raw[1]}"
        self._update(set_key, where_key)
