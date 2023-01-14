"""React Roles are pairs between a Reaction (emoji) and a Role. By binding
the reaction to a message, once reacted upon the bound role will be given to
the user.
"""
from typing import Optional

from db.react_roles import RoleDb, ReactRoleRaw


def make_raw(role_id: int) -> ReactRoleRaw:
    """Creates a raw react role (tuple) fit for storing into a database with
    pre-defined defaults.
    """
    return (role_id, 0, "", False)


class ReactRole():
    """Representation of a React Role pair. Initialized with ReactRoleRaw."""

    def __init__(self, raw: ReactRoleRaw):
        self.role_id = raw[0]
        self.guild_id = raw[1]
        self.reaction = raw[2].replace("'", '')
        self.reversed = raw[3]

    @property
    def _raw(self) -> ReactRoleRaw:
        """Convers the ReactRole back into a ReactRoleRaw."""
        return (self.role_id, self.guild_id,
                f"'{self.reaction}'", self.reversed)

    def save(self) -> None:
        """Stores the React Role pair into the database, saving or updating
        as necessary.
        """
        if Manager._db:
            Manager._db.update(self._raw)

    def delete(self) -> None:
        """Removes the React Role pair from the database."""
        if Manager._db:
            Manager._db.delete_one(self._raw)


class Manager():
    """Manages the ReactRole database in memory and in storage."""
    _db: Optional[RoleDb] = None
    _react_roles: dict[int, ReactRole] = {}

    @staticmethod
    def init(dbname: str) -> None:
        """Initializes the React Roles Manager, connection and loading
        from the database.
        """
        Manager._db = RoleDb(dbname)
        raw_roles = Manager._db.find_all()
        for raw in raw_roles:
            Manager.add(ReactRole(raw))

    @staticmethod
    def add(react_role: ReactRole) -> ReactRole:
        """Adds a ReactRole to memory, does not save it to database."""
        Manager._react_roles[react_role.role_id] = react_role
        return react_role

    @staticmethod
    def remove(react_role: ReactRole) -> None:
        """Removes a ReactRole from memory, not database."""
        Manager._react_roles.pop(react_role.role_id, None)

    @staticmethod
    def get(role_id: int) -> Optional[ReactRole]:
        """Obtains a ReactRole if it exists, otherwise returns None."""
        return Manager._react_roles.get(role_id)

    @staticmethod
    def guild_roles(guild_id: int) -> list[ReactRole]:
        """Obtains all of the ReactRoles for the specified guild."""
        guild_roles: list[ReactRole] = []
        for value in Manager._react_roles.values():
            # Check that it is the correct guild id.
            if value.guild_id == guild_id:
                guild_roles.append(value)
        return guild_roles

    @staticmethod
    def find(guild_id: int, reaction: str) -> Optional[ReactRole]:
        """Find a ReactRole based on the guild it belongs to and the reaction
        that is used to trigger it.
        """
        for value in Manager._react_roles.values():
            if value.guild_id == guild_id:
                if value.reaction.strip("'") == reaction.strip("'"):
                    return value
