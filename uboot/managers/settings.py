# 0: int - guild_id
# 1: int - market_channel_id
# 2: int - react_role_channel_id
# 3: int - react_role_msg_id
# 4: int - expiration_days
GuildSettingsRaw = tuple[int, int, int, int, int]


def make_raw(guild_id: int) -> GuildSettingsRaw:
    return (guild_id, 0, 0, 0, 30)


class Settings():
    def __init__(self, raw: GuildSettingsRaw) -> None:
        self.guild_id = raw[0]
        self.market_channel_id = raw[1]
        self.react_role_channel_id = raw[2]
        self.react_role_msg_id = raw[3]
        self.expiration_days = raw[4]

    @property
    def _raw(self) -> GuildSettingsRaw:
        return (self.guild_id, self.market_channel_id,
                self.react_role_channel_id, self.react_role_msg_id,
                self.expiration_days)


class Manager():
    _guilds: dict[int, Settings] = {}

    @staticmethod
    def add(setting: Settings) -> Settings:
        Manager._guilds[setting.guild_id] = setting
        return setting

    @staticmethod
    def get(guild_id: int) -> Settings:
        setting = Manager._guilds.get(guild_id)
        if not setting:
            setting = Settings(make_raw(guild_id))
            Manager.add(setting)
        return setting
