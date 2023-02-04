"""Sub-guilds are privatized Discord threads within the greater guild.
The associated manager handles all the loading and saving to database. It is
also equipped with finding aliases based on certain parameters.
"""
from typing import Optional

from db.aliases import AliasDb, AliasRaw


def make_raw(guild_id: int, alias_id: int) -> AliasRaw:
    """Creates a raw alias (tuple) fit for storing into a database with
    pre-defined defaults.
    """
    return alias_id, guild_id, 0, "unknown", 0


class Alias:
    """Representation of an alias. Initialized with AliasRaw."""

    def __init__(self, raw: AliasRaw) -> None:
        self.id = raw[0]
        self.guild_id = raw[1]
        self.msg_id = raw[2]
        self.name = raw[3].strip("'")
        self.owner_id = raw[4]

    def __str__(self) -> str:
        return f"**{self.name}** [{self.msg_id}] by: <@{self.owner_id}>"

    @property
    def _raw(self) -> AliasRaw:
        """Converts the Alias into an AliasRaw."""
        return (self.id, self.guild_id, self.msg_id,
                f"'{self.name}'", self.owner_id)

    def save(self) -> None:
        """Stores the Alias into the database, saving or updating
        as necessary.
        """
        if Manager.db:
            Manager.db.update(self._raw)

    def delete(self) -> None:
        """Removes the Alias from the database."""
        if Manager.db:
            Manager.db.delete_one(self._raw)


class Manager:
    """Manages the Alias database in memory and in storage."""
    db: Optional[AliasDb] = None
    _aliases: dict[int, dict[int, Alias]] = {}

    @staticmethod
    def init(dbname: str) -> None:
        """Initializes the Alias Manager, connecting and loading from
        database.
        """
        Manager.db = AliasDb(dbname)
        raw_aliases = Manager.db.find_all()
        for raw in raw_aliases:
            Manager.add(Alias(raw))

    @staticmethod
    def last_id(guild_id: int) -> int:
        """Gets the most recent ID created for a particular guild.
        Defaults to 0 if there is none."""
        if not Manager.db:
            raise ValueError("could not get last alias id, no db.")

        last = Manager.db.find_last(guild_id)
        if last:
            return Alias(last).id
        return 0

    @staticmethod
    def total(guild_id: int) -> int:
        """Gets the current total of aliases."""
        guild_aliases = Manager._aliases.get(guild_id)
        if not guild_aliases:
            # Initialize the guild.
            Manager._aliases[guild_id] = {}
            return 0

        return len(guild_aliases.keys())

    @staticmethod
    def add(alias: Alias) -> Alias:
        """Add an alias to memory, does not save it to database."""
        guild_aliases = Manager._aliases.get(alias.guild_id)
        if not guild_aliases:
            # Create the guild.
            Manager._aliases[alias.guild_id] = {}

        # Add to the guild.
        Manager._aliases[alias.guild_id][alias.id] = alias
        return alias

    @staticmethod
    def by_name(guild_id: int, name: str) -> Optional[Alias]:
        """Finds an alias by its name."""
        guild_aliases = Manager._aliases.get(guild_id)
        if not guild_aliases:
            # No aliases for guild, none exist.
            return None

        # Attempt to resolve the name.
        for value in guild_aliases.values():
            if value.name == name:
                return value
        return None

    @staticmethod
    def get(guild_id: int, alias_id: int) -> Alias:
        """Get an alias from a guild based on its id. If it does not exist,
        it will be initialized with defaults.
        """
        guild_aliases = Manager._aliases.get(guild_id)
        if not guild_aliases:
            # Guild does not exist, create guild and alias.
            alias = Alias(make_raw(guild_id, alias_id))
            return Manager.add(alias)

        alias = guild_aliases.get(alias_id)
        if not alias:
            # Alias was not found, create and add it.
            alias = Alias(make_raw(guild_id, alias_id))
            Manager.add(alias)
        return alias

    @staticmethod
    def get_all(guild_id: int) -> list[Alias]:
        """Gets all the aliases for a guild."""
        guild_aliases = Manager._aliases.get(guild_id)
        if not guild_aliases:
            return []

        return list(guild_aliases.values())

    @staticmethod
    def remove(guild_id: int, name: str) -> bool:
        """Removes an alias by name."""
        alias = Manager.by_name(guild_id, name.lower())
        if not alias:
            return False

        # Remove it from the database.
        alias.delete()

        # Remove it from memory.
        guild_aliases = Manager._aliases.get(guild_id)
        if not guild_aliases:
            return False

        if guild_aliases.get(alias.id):
            del guild_aliases[alias.id]

        return True
