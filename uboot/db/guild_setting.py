from typing import Optional
from .db_socket import DbSocket

from managers import settings


class GuildSettingDb(DbSocket):
    def __init__(self, filename: str) -> None:
        super().__init__(filename)
        self.query['create_table'] = "CREATE TABLE IF NOT EXISTS [{table_name}] "\
            "( guild_id INTEGER PRIMARY KEY DESC, "\
            "market_channel_id INTEGER, react_role_channel_id INTEGER, "\
            "react_role_msg_id INTEGER, expiration_days INTEGER, "\
            "support_channel_id INTEGER, support_role_id INTEGER, "\
            "suggestion_channel_id INTEGER, "\
            "suggestion_reviewer_role_id INTEGER )"
        self.query['save_many'] = "INSERT OR IGNORE INTO [{table_name}] "\
            "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)"
        self.query['insert'] = "INSERT INTO {table_name} "\
            "VALUES ({value_key}) ON CONFLICT(guild_id) "\
            "DO UPDATE SET {set_key}"
        self.query['delete'] = "DELETE FROM {table_name} WHERE "\
            "{condition}"
        self.query['load_many'] = "SELECT * FROM [{table_name}]"

    def save_many(self, setting: list[settings.Settings]) -> None:
        if len(setting) == 0:
            return
        items = list(map(lambda s: s._raw, setting))
        self._save_many("guild", items)

    def update(self, settings: settings.Settings) -> None:
        s = settings
        value_key = f"{s.guild_id}, {s.market_channel_id}, "\
            f"{s.react_role_channel_id}, {s.react_role_msg_id}, "\
            f"{s.expiration_days}, {s.support_channel_id}, "\
            f"{s.support_role_id}, {s.suggestion_channel_id}, "\
            f"{s.suggestion_reviewer_role_id}"
        set_key = f"market_channel_id = {s.market_channel_id}, "\
            f"react_role_channel_id = {s.react_role_channel_id}, "\
            f"react_role_msg_id = {s.react_role_msg_id}, "\
            f"expiration_days = {s.expiration_days}, "\
            f"support_channel_id = {s.support_channel_id}, "\
            f"support_role_id = {s.support_role_id}, "\
            f"suggestion_channel_id = {s.suggestion_channel_id}, "\
            f"suggestion_reviewer_role_id = {s.suggestion_reviewer_role_id}"
        self._insert("guild", value_key, set_key)

    def load_many(self) -> list[settings.Settings]:
        raw_settings = self._load_many("guild", "")
        return [settings.Manager.add(settings.Settings(s))
                for s in raw_settings]
