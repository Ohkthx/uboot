"""Sub-guilds are privatized Discord threads within the greater guild.
The associated manager handles all the loading and saving to database. It is
also equipped with finding sub-guilds based on certain parameters.
"""
from typing import Optional
import json

from db.subguilds import SubGuildDb, SubGuildRaw


def make_raw(guild_id: int, subguild_id: int) -> SubGuildRaw:
    """Creates a raw subguild (tuple) fit for storing into a database with
    pre-defined defaults.
    """
    return subguild_id, guild_id, "unknown", 0, 0, 0, True, '[]'


class SubGuild:
    """Representation of a subguild. Initialized with SubGuildRaw."""

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
        """Converts the SubGuild into a SubGuildRaw."""
        return (self.id, self.guild_id, f"'{self.name}'", self.owner_id,
                self.thread_id, self.msg_id, self.disabled,
                f"'{json.dumps(self.banned)}'")

    def save(self) -> None:
        """Stores the SubGuild into the database, saving or updating
        as necessary.
        """
        if Manager.db:
            Manager.db.update(self._raw)


class Manager:
    """Manages the SubGuild database in memory and in storage."""
    db: Optional[SubGuildDb] = None
    _subguilds: dict[int, dict[int, SubGuild]] = {}

    @staticmethod
    def init(dbname: str) -> None:
        """Initializes the SubGuild Manager, connecting and loading from
        database.
        """
        Manager.db = SubGuildDb(dbname)
        raw_subguilds = Manager.db.find_all()
        for raw in raw_subguilds:
            Manager.add(SubGuild(raw))

    @staticmethod
    def last_id(guild_id: int) -> int:
        """Gets the most recent ID created for a particular guild.
        Defaults to 0 if there is none."""
        if not Manager.db:
            raise ValueError("could not get last subguild id, no db.")

        last = Manager.db.find_last(guild_id)
        if last:
            return SubGuild(last).id
        return 0

    @staticmethod
    def total(guild_id: int) -> int:
        """Gets the current total of subguilds."""
        guild_subguilds = Manager._subguilds.get(guild_id)
        if not guild_subguilds:
            # Initialize the guild.
            Manager._subguilds[guild_id] = {}
            return 0

        return len(guild_subguilds.keys())

    @staticmethod
    def add(subguild: SubGuild) -> SubGuild:
        """Add a subguild to memory, does not save it to database."""
        guild_subguilds = Manager._subguilds.get(subguild.guild_id)
        if not guild_subguilds:
            # Create the guild.
            Manager._subguilds[subguild.guild_id] = {}

        # Add to the guild.
        Manager._subguilds[subguild.guild_id][subguild.id] = subguild
        return subguild

    @staticmethod
    def by_name(guild_id: int, name: str) -> Optional[SubGuild]:
        """Finds a subguild by its name."""
        guild_subguilds = Manager._subguilds.get(guild_id)
        if not guild_subguilds:
            # No subguilds for guild, none exist.
            return None

        # Attempt to resolve the name.
        for value in guild_subguilds.values():
            if value.name == name:
                return value
        return None

    @staticmethod
    def by_thread(guild_id: int, thread_id: int) -> Optional[SubGuild]:
        """Attempt to find the subguild based on its thread's id."""
        guild_subguilds = Manager._subguilds.get(guild_id)
        if not guild_subguilds:
            # No subguilds for guild, none exist.
            return None

        # Attempt to resolve the thread id.
        for value in guild_subguilds.values():
            if value.thread_id == thread_id:
                return value
        return None

    @staticmethod
    def get(guild_id: int, subguild_id: int) -> SubGuild:
        """Get a subguild from a guild based on its id. If it does not exist,
        it will be initialized with defaults.
        """
        guild_subguilds = Manager._subguilds.get(guild_id)
        if not guild_subguilds:
            # Guild does not exist, create guild and subguild.
            subguild = SubGuild(make_raw(guild_id, subguild_id))
            return Manager.add(subguild)

        subguild = guild_subguilds.get(subguild_id)
        if not subguild:
            # SubGuild was not found, create and add it.
            subguild = SubGuild(make_raw(guild_id, subguild_id))
            Manager.add(subguild)
        return subguild
