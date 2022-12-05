from typing import Optional
from .db_socket import DbSocket, clean_name

# 0: int - guild_id
# 1: int - market_channel_id
# 2: int - react_role_channel_id
# 3: int - react_role_msg_id
# 4: int - expiration_days
# 5: int - support_channel
# 6: int - support_role_id
# 7: int - suggestion_channel_id
# 8: int - suggestion_reviewer_role_id
GuildSettingsRaw = tuple[int, int, int, int, int, int, int, int, int]


class GuildSettingDb(DbSocket):
    def __init__(self, filename: str) -> None:
        super().__init__(filename)
        self.table_name = clean_name('guild_settings')
        self.query['create_table'] = "CREATE TABLE IF NOT EXISTS {table_name} "\
            "( guild_id INTEGER PRIMARY KEY DESC, "\
            "market_channel_id INTEGER, react_role_channel_id INTEGER, "\
            "react_role_msg_id INTEGER, expiration_days INTEGER, "\
            "support_channel_id INTEGER, support_role_id INTEGER, "\
            "suggestion_channel_id INTEGER, "\
            "suggestion_reviewer_role_id INTEGER )"
        self.query['insert_one'] = "INSERT OR IGNORE INTO {table_name} "\
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"

    def find_one(self, guild_id: int) -> Optional[GuildSettingsRaw]:
        where_key = f"guild_id = {guild_id}"
        return self._find_one(where_key)

    def find_all(self) -> list[GuildSettingsRaw]:
        return self._find_many()

    def insert_one(self, raw: GuildSettingsRaw) -> None:
        self._insert_one(raw)

    def update(self, raw: GuildSettingsRaw) -> None:
        old = self.find_one(raw[0])
        if not old:
            return self.insert_one(raw)

        set_key = f"market_channel_id = {raw[1]}, "\
            f"react_role_channel_id = {raw[2]}, "\
            f"react_role_msg_id = {raw[3]}, "\
            f"expiration_days = {raw[4]}, "\
            f"support_channel_id = {raw[5]}, "\
            f"support_role_id = {raw[6]}, "\
            f"suggestion_channel_id = {raw[7]}, "\
            f"suggestion_reviewer_role_id = {raw[8]}"
        where_key = f"guild_id = {raw[0]}"
        self._update(set_key, where_key)