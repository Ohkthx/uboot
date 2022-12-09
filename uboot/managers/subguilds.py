from typing import Optional
import json

from db.subguilds import SubGuildDb, SubGuildRaw


def make_raw(guild_id: int, id: int) -> SubGuildRaw:
    return (id, guild_id, "unknown", 0, 0, 0, True, '[]')


class SubGuild():
    def __init__(self, raw: SubGuildRaw) -> None:
        self.id = raw[0]
        self.guild_id = raw[1]
        self.name = raw[2].strip("'")
        self.owner_id = raw[3]
        self.thread_id = raw[4]
        self.msg_id = raw[5]
        self.disabled = raw[6]
        self.banned: list[int] = json.loads(raw[7])

    @property
    def _raw(self) -> SubGuildRaw:
        return (self.id, self.guild_id, f"'{self.name}'", self.owner_id,
                self.thread_id, self.msg_id, self.disabled,
                f"'{json.dumps(self.banned)}'")

    def save(self) -> None:
        if Manager._db:
            Manager._db.update(self._raw)


class Manager():
    _db: Optional[SubGuildDb] = None
    _subguilds: dict[int, dict[int, SubGuild]] = {}

    @staticmethod
    def init(dbname: str) -> None:
        Manager._db = SubGuildDb(dbname)
        raw_subguilds = Manager._db.find_all()
        for raw in raw_subguilds:
            Manager.add(SubGuild(raw))

    @staticmethod
    def last_id(guild_id: int) -> int:
        if not Manager._db:
            raise ValueError("could not get last subguild id, no db.")

        last = Manager._db.find_last(guild_id)
        if last:
            return SubGuild(last).id
        return 0

    @staticmethod
    def total(guild_id: int) -> int:
        guild_subguilds = Manager._subguilds.get(guild_id)
        if not guild_subguilds:
            Manager._subguilds[guild_id] = {}
            return 0

        return len(guild_subguilds.keys())

    @staticmethod
    def add(subguild: SubGuild) -> SubGuild:
        guild_subguilds = Manager._subguilds.get(subguild.guild_id)
        if not guild_subguilds:
            Manager._subguilds[subguild.guild_id] = {}

        Manager._subguilds[subguild.guild_id][subguild.id] = subguild
        return subguild

    @staticmethod
    def by_name(guild_id: int, name: str) -> Optional[SubGuild]:
        guild_subguilds = Manager._subguilds.get(guild_id)
        if not guild_subguilds:
            return None

        for value in guild_subguilds.values():
            if value.name == name:
                return value
        return None

    @staticmethod
    def by_thread(guild_id: int, thread_id: int) -> Optional[SubGuild]:
        guild_subguilds = Manager._subguilds.get(guild_id)
        if not guild_subguilds:
            return None

        for value in guild_subguilds.values():
            if value.thread_id == thread_id:
                return value
        return None

    @staticmethod
    def get(guild_id: int, id: int) -> SubGuild:
        guild_subguilds = Manager._subguilds.get(guild_id)
        if not guild_subguilds:
            subguild = SubGuild(make_raw(guild_id, id))
            return Manager.add(subguild)

        subguild = guild_subguilds.get(id)
        if not subguild:
            subguild = SubGuild(make_raw(guild_id, id))
            Manager.add(subguild)
        return subguild
