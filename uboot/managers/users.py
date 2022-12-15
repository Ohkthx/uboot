"""Representation of a user. Keeps track of several settings and manages the
connection between database and memory.
"""
from datetime import datetime, timedelta
from typing import Optional

from db.users import UserDb, UserRaw


def make_raw(user_id: int) -> UserRaw:
    """Creates a raw user (tuple) fit for storing into a database with
    pre-defined defaults.
    """
    return (user_id, 100, 0, 0, 0, 0)


class User():
    """Representation of a user. Initialized with UserRaw."""

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
        """Overrides str to just display some basics."""
        return f"id: {self.id}, gold: {self._gold}, msgs: {self.msg_count}"

    @property
    def _raw(self) -> UserRaw:
        """Convers the User back into a UserRaw."""
        return (self.id, self._gold, self.msg_count, self.gambles,
                self.gambles_won, self.button_press)

    @property
    def gold(self) -> int:
        """Displays the current amount of gold a user has. If the user is the
        bot, it does additional calculations to determine gold amount.
        """
        if not self.isbot:
            # Non-bot defaults to its gold amount.
            return self._gold

        total: int = 0
        # Get the amount of "lost" gold for each user and add it up.
        for user in Manager.getall():
            if user.isbot or user._gold >= user.msg_count or user._gold < 0:
                # Ignore bot or negative amounts.
                continue
            total += (user.msg_count - user._gold)
        return total

    @gold.setter
    def gold(self, val) -> None:
        """Setter for accessing protected gold property."""
        self._gold = val

    def save(self) -> None:
        """Saves the user in memory to database."""
        if Manager._db:
            Manager._db.update(self._raw)

    def add_message(self, multiplier: float = 1.0) -> None:
        """Adds a message to the user. Rewards with gold if off cooldown."""
        self.msg_count += 1

        # Check if it adding gold is off of cooldown.
        now = datetime.now()
        time_diff = now - self.last_message
        if time_diff >= timedelta(seconds=15):
            # Gold is not on cooldown, add.
            self.gold = int(self.gold + (1 * multiplier))
            self.last_message = now

    def win_rate(self) -> float:
        """Calculate the win-rate percentage for gambling."""
        if self.gambles == 0:
            return 0
        return (1 + (self.gambles_won - self.gambles) /
                self.gambles) * 100

    def minimum(self, floor: int) -> int:
        """Gets the current gambling minimum."""
        minimum_offset = int(self.gold * 0.1)
        # Gold has to be AT LEAST the floor.
        return minimum_offset if minimum_offset > floor else floor


class Manager():
    """Manages the User database in memory and in storage."""
    _db: Optional[UserDb] = None
    _users: dict[int, User] = {}

    @staticmethod
    def init(dbname: str) -> None:
        """Initializes the User Manager, connecting and loading from
        database.
        """
        Manager._db = UserDb(dbname)
        raw_users = Manager._db.find_all()
        for raw in raw_users:
            Manager.add(User(raw))

    @staticmethod
    def add(user: User) -> User:
        """Adds a user to memory, does not save it to database."""
        Manager._users[user.id] = user
        return user

    @staticmethod
    def get(user_id: int) -> User:
        """Get a user from a guild based on its id. If it does not exist,
        it will be initialized with defaults.
        """
        user = Manager._users.get(user_id)
        if not user:
            # Create and add it to the manager.
            user = User(make_raw(user_id))
            Manager.add(user)
        return user

    @staticmethod
    def getall() -> list[User]:
        """Gets all of the users being managed."""
        return list(Manager._users.values())
