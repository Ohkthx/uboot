from datetime import datetime, timedelta
from typing import Optional

from db.users import UserDb, UserRaw


def make_raw(user_id: int) -> UserRaw:
    return (user_id, 100, 0, 0, 0, 0)


class User():
    def __init__(self, raw: UserRaw) -> None:
        self.id = raw[0]
        self._gold = raw[1]
        self.msg_count = raw[2]
        self.gambles = raw[3]
        self.gambles_won = raw[4]
        self.button_press = raw[5]
        self.isbot = False
        self.last_message = datetime.now() - timedelta(seconds=20)

    def __str__(self) -> str:
        return f"id: {self.id}, gold: {self._gold}, msgs: {self.msg_count}"

    @property
    def _raw(self) -> UserRaw:
        return (self.id, self._gold, self.msg_count, self.gambles,
                self.gambles_won, self.button_press)

    @property
    def gold(self) -> int:
        if not self.isbot:
            return self._gold

        total: int = 0
        for user in Manager.getall():
            if user.isbot or user._gold >= user.msg_count or user._gold < 0:
                continue
            total += (user.msg_count - user._gold)
        return total

    @gold.setter
    def gold(self, val) -> None:
        self._gold = val

    def save(self) -> None:
        if Manager._db:
            Manager._db.update(self._raw)

    def add_message(self) -> None:
        self.msg_count += 1
        now = datetime.now()
        time_diff = now - self.last_message
        if time_diff >= timedelta(seconds=15):
            self.gold += 1
            self.last_message = now

    def win_rate(self) -> float:
        if self.gambles == 0:
            return 0
        return (1 + (self.gambles_won - self.gambles) /
                self.gambles) * 100

    def minimum(self, floor: int) -> int:
        minimum_offset = int(self.gold * 0.1)
        return minimum_offset if minimum_offset > floor else floor


class Manager():
    _db: Optional[UserDb] = None
    _users: dict[int, User] = {}

    @staticmethod
    def init(dbname: str) -> None:
        Manager._db = UserDb(dbname)
        raw_users = Manager._db.find_all()
        for raw in raw_users:
            Manager.add(User(raw))

    @staticmethod
    def add(user: User) -> User:
        Manager._users[user.id] = user
        return user

    @staticmethod
    def get(user_id: int) -> User:
        user = Manager._users.get(user_id)
        if not user:
            user = User(make_raw(user_id))
            Manager.add(user)
        return user

    @staticmethod
    def getall() -> list[User]:
        return list(Manager._users.values())
