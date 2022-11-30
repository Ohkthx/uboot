from .role import RoleDb
from .user import UserDb
from .guild_setting import GuildSettingDb
from .ticket import TicketDb


class SqliteDb():
    def __init__(self, suffix: str = "", filetype: str = "sqlite3") -> None:
        if suffix != "" and not suffix.startswith("_"):
            suffix = f"_{suffix}"
        self._role_db = RoleDb(f"dbs/uboot{suffix}.{filetype}")
        self._user_db = UserDb(f"dbs/uboot{suffix}.{filetype}")
        self._guild_db = GuildSettingDb(f"dbs/uboot{suffix}.{filetype}")
        self._ticket_db = TicketDb(f"dbs/uboot{suffix}.{filetype}")

    @property
    def role(self) -> RoleDb:
        return self._role_db

    @property
    def user(self) -> UserDb:
        return self._user_db

    @property
    def guild(self) -> GuildSettingDb:
        return self._guild_db

    @property
    def ticket(self) -> TicketDb:
        return self._ticket_db

    @property
    def is_saving(self) -> bool:
        return self.role.is_saving
