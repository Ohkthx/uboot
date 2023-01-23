"""Representation of a user. Keeps track of several settings and manages the
connection between database and memory.
"""
import json
import math
import random
from datetime import datetime, timedelta
from typing import Optional

from db.users import UserDb, UserRaw
from .banks import Manager as BankManager
from .locations import Locations, Area
from .loot_tables import Item, Chest, Items, Material, ItemRaw


def make_raw(user_id: int) -> UserRaw:
    """Creates a raw user (tuple) fit for storing into a database with
    pre-defined defaults.
    """
    return (user_id, 100, 0, 0, 0, 0, 0, 0, 0,
            Area.SEWERS.value, Area.SEWERS.value, 0, "''")


class User():
    """Representation of a user. Initialized with UserRaw."""

    def __init__(self, raw: UserRaw) -> None:
        self.id = raw[0]
        self._gold = raw[1]
        self.msg_count = raw[2]
        self.gambles = raw[3]
        self.gambles_won = raw[4]
        self.button_press = raw[5]
        self.monsters = raw[6]
        self.kills = raw[7]
        self._exp = raw[8]
        self.locations: Locations = Locations(raw[9])
        self.c_location: Area = Area(raw[10])
        if not self.locations.is_unlocked(self.c_location):
            self.c_location = Area.SEWERS
        self._deaths = raw[11]

        self.weapon: Optional[Item] = None
        if raw[12].replace("'", '') != "":
            weapon_raw: ItemRaw = json.loads(raw[12].replace("'", ''))
            self.weapon = Item.from_raw(weapon_raw)

        self.isbot = False
        self._incombat = False
        self.powerhour: Optional[datetime] = None
        self.last_message = datetime.now() - timedelta(hours=6)
        self.last_taunt = self.last_message

        self.bank = BankManager.get(self.id)

    def __str__(self) -> str:
        """Overrides str to just display some basics."""
        return f"id: {self.id}, gold: {self._gold}, msgs: {self.msg_count}"

    @property
    def _raw(self) -> UserRaw:
        """Convers the User back into a UserRaw."""
        gold = self.gold
        if self.isbot:
            gold = self._gold

        weapon = "''"
        if self.weapon:
            weapon = f"'{json.dumps(self.weapon._raw)}'"
        return (self.id, gold, self.msg_count, self.gambles,
                self.gambles_won, self.button_press,
                self.monsters, self.kills, self.exp,
                self.locations.raw, self.c_location.value,
                self._deaths, weapon)

    @property
    def incombat(self) -> bool:
        """Checks if the user is in combat or not."""
        return self._incombat

    def durability_loss(self, value: int) -> None:
        """Removes durability from weapons/armor."""
        if not self.weapon:
            return

        self.weapon.remove_use(value)

        # Destroy the weapon if the uses are now 0.
        if self.weapon.uses == 0:
            self.weapon = None

    def set_combat(self, value: bool) -> None:
        """Set the user to be in combat."""
        self._incombat = value

    @property
    def gold(self) -> int:
        """Displays the current amount of gold a user has. If the user is the
        bot, it does additional calculations to determine gold amount.
        """
        if not self.isbot:
            # Non-bot defaults to its gold amount.
            return int(self._gold)

        total: int = 0
        # Get the amount of "lost" gold for each user and add it up.
        for user in Manager.getall():
            if user.isbot or user._gold >= user.msg_count or user._gold < 0:
                # Ignore bot or negative amounts.
                continue
            total += (user.msg_count - user._gold)
        return int(total)

    @gold.setter
    def gold(self, val) -> None:
        """Setter for accessing protected gold property."""
        self._gold = val
        self._gold = max(self._gold, 0)

        # Player has died.
        if self.msg_count > 0 and self._gold == 0:
            self.deaths += 1

    @property
    def deaths(self) -> int:
        """Displays the current amount of deaths a user has."""
        return max(self._deaths, 0)

    @deaths.setter
    def deaths(self, val) -> None:
        """Setter for accessing protected deaths property."""
        self._deaths = val
        self._deaths = max(self._deaths, 0)

    @property
    def exp(self) -> int:
        """Ensures EXP is rendered as an int."""
        return int(self._exp)

    @exp.setter
    def exp(self, val) -> None:
        """Setter for accessing protected exp property."""
        self._exp = val

    def save(self) -> None:
        """Saves the user in memory to database."""
        if Manager._db:
            Manager._db.update(self._raw)

    def change_location(self, destination: str) -> bool:
        """Attempts to change the users location."""
        new_loc: Optional[Area] = None
        for area in Area:
            if not self.locations.is_unlocked(area) or not area.name:
                continue
            if area.name.lower() == destination.lower():
                new_loc = area
                break

        if not new_loc:
            return False
        self.c_location = new_loc
        return True

    def apply_loot(self, loot: list[Item], allow_area: bool) -> Optional[Area]:
        """Applys various items to the user. If a new area is unlocked, it will
        return the new area.
        """
        new_area: Optional[Area] = None
        for item in loot:
            if item.type == Items.GOLD:
                self.gold += item.value
            elif item.type == Items.CHEST and isinstance(item, Chest):
                self.apply_loot(item.items, allow_area)
            elif item.type in (Items.POWERHOUR, Items.WEAPON, Items.TRASH):
                self.bank.add_item(item)
                self.bank.save()
            elif item.type == Items.LOCATION and allow_area:
                # Get all connections, removing the ones already discovered.
                conn = self.locations.connections(self.c_location)
                conn = [l for l in conn if not self.locations.is_unlocked(l)]
                if len(conn) == 0:
                    continue

                new_area = conn[random.randrange(0, len(conn))]
                self.locations.unlock(new_area)
        return new_area

    @property
    def level(self) -> int:
        """Calculates the level of the user based on their exp."""
        raw = math.pow(self.exp / 50, 1 / 2.75) - 1
        if raw < 1:
            return 1
        if raw > 20:
            return 20 * 6

        return int(raw * 6)

    @property
    def difficulty(self) -> float:
        """Calculates the difficulty of the user."""
        if self.isbot:
            return 0.0

        material = self.weapon.material if self.weapon else Material.NONE

        level_offset = self.level / 100
        gold_offset = self.gold / (max(self.msg_count, 1) * 3)
        weapon_offset = (max(material, Material.NONE) - 1) / 20
        total_offset = level_offset + gold_offset + weapon_offset + 1
        if self.level == 1:
            # New player protection.
            if self.exp < 100.0:
                return 1.0
            return min(total_offset, 1.25)
        return min(total_offset, 5)

    @property
    def gold_multiplier_powerhour(self) -> float:
        """Get the users modified powerhour gold per message."""
        return 2.0

    @property
    def gold_multiplier(self) -> float:
        """Generates a gold multiplier based on the players level."""
        if self.isbot:
            return 0.0
        return max(math.log(self.level / 6, 400) + 1, 1.0)

    def add_message(self, multiplier: float = 1.0) -> None:
        """Adds a message to the user. Rewards with gold if off cooldown."""
        self.msg_count += 1

        now = datetime.now()
        if self.powerhour:
            time_diff = now - self.powerhour
            if time_diff < timedelta(hours=1):
                multiplier += self.gold_multiplier_powerhour
            else:
                self.powerhour = None

        # Check if it adding gold is off of cooldown.
        time_diff = now - self.last_message
        if time_diff < timedelta(seconds=15):
            return

        # Gold is not on cooldown, add.
        total_multiplier = self.gold_multiplier
        if multiplier >= 1.0:
            total_multiplier += (multiplier - 1)
        self.gold = self._gold + (1 * total_multiplier)
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
