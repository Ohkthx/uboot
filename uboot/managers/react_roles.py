from typing import Optional

from db.react_roles import RoleDb, ReactRoleRaw


def make_raw(role_id: int) -> ReactRoleRaw:
    return (role_id, 0, "", False)


class ReactRole():
    def __init__(self, raw: ReactRoleRaw):
        self.role_id = raw[0]
        self.guild_id = raw[1]
        self.reaction = raw[2]
        self.reversed = raw[3]

    @property
    def _raw(self) -> ReactRoleRaw:
        return (self.role_id, self.guild_id,
                f"'{self.reaction}'", self.reversed)

    def save(self) -> None:
        if Manager._db:
            Manager._db.update(self._raw)

    def delete(self) -> None:
        if Manager._db:
            Manager._db.delete_one(self._raw)


class Manager():
    _db: Optional[RoleDb] = None
    _react_roles: dict[int, ReactRole] = {}

    @staticmethod
    def init(dbname: str) -> None:
        Manager._db = RoleDb(dbname)
        raw_roles = Manager._db.find_all()
        for raw in raw_roles:
            Manager.add(ReactRole(raw))

    @staticmethod
    def add(react_role: ReactRole) -> ReactRole:
        Manager._react_roles[react_role.role_id] = react_role
        return react_role

    @staticmethod
    def remove(react_role: ReactRole) -> None:
        Manager._react_roles.pop(react_role.role_id, None)

    @staticmethod
    def get(role_id: int) -> Optional[ReactRole]:
        return Manager._react_roles.get(role_id)

    @staticmethod
    def guild_roles(guild_id: int) -> list[ReactRole]:
        guild_roles: list[ReactRole] = []
        for value in Manager._react_roles.values():
            if value.guild_id == guild_id:
                guild_roles.append(value)
        return guild_roles

    @staticmethod
    def find(guild_id: int, reaction: str) -> Optional[ReactRole]:
        for value in Manager._react_roles.values():
            if value.guild_id == guild_id and value.reaction == reaction:
                return value
