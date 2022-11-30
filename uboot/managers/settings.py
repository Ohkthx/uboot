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


def make_raw(guild_id: int) -> GuildSettingsRaw:
    return (guild_id, 0, 0, 0, 30, 0, 0, 0, 0)


class Settings():
    def __init__(self, raw: GuildSettingsRaw) -> None:
        self.guild_id = raw[0]
        self.market_channel_id = raw[1]
        self.react_role_channel_id = raw[2]
        self.react_role_msg_id = raw[3]
        self.expiration_days = raw[4]
        self.support_channel_id = raw[5]
        self.support_role_id = raw[6]
        self.suggestion_channel_id = raw[7]
        self.suggestion_reviewer_role_id = raw[8]

    @property
    def _raw(self) -> GuildSettingsRaw:
        return (self.guild_id, self.market_channel_id,
                self.react_role_channel_id, self.react_role_msg_id,
                self.expiration_days, self.support_channel_id,
                self.support_role_id, self.suggestion_channel_id,
                self.suggestion_reviewer_role_id)


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
