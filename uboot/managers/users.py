"""Representation of a user. Keeps track of several settings and manages the
connection between database and memory.
"""
import math
import random
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Optional

from db.users import UserDb, UserRaw
from .inventories import Manager as BagManager
from .items import Item, Chest, Items, Material, Manager as ItemManager
from .locations import Floor, Level, Locations, Area, Manager as LocationsManager


def make_raw(user_id: int) -> UserRaw:
    """Creates a raw user (tuple) fit for storing into a database with
    pre-defined defaults.
    """
    return (user_id, 100, 0, 0, 0, 0, 0, 0, 0,
            Area.BRITAIN_SEWERS.value, Area.BRITAIN_SEWERS.value,
            0, "''", Level.ONE, 0, "''")


class Cooldown(Enum):
    """Various cooldowns that a user can have."""
    GOLD = auto()
    POWERHOUR = auto()
    TAUNT = auto()
    FORAGE = auto()
    MINING = auto()


class User:
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
            self.c_location = Area.BRITAIN_SEWERS
        self.c_floor = Level(raw[13])
        self.is_streamer = bool(raw[14])

        if not raw[15]:
            self.stream_name = ""
        else:
            self.stream_name: str = raw[15].replace("'", "")

        self._deaths = raw[11]

        weapon_id: str = raw[12].replace("'", "")
        self.weapon: Optional[Item] = None
        if weapon_id != "":
            weapon = ItemManager.get(weapon_id)
            if weapon and weapon.type == Items.WEAPON:
                self.weapon = weapon

        self.is_bot = False
        self._in_combat = False

        self._cooldowns: dict[Cooldown, datetime] = {}
        self.backpack = BagManager.get_backpack(self.id)
        self.bank = BagManager.get_bank(self.id)

    def __str__(self) -> str:
        """Overrides str to just display some basics."""
        return f"id: {self.id}, gold: {self._gold}, msgs: {self.msg_count}"

    @property
    def raw(self) -> UserRaw:
        """Converts the User back into a UserRaw."""
        gold = self.gold
        if self.is_bot:
            gold = self._gold

        weapon = "''"
        if self.weapon:
            weapon = f"'{self.weapon.id}'"

        stream_name = "''"
        if self.stream_name:
            stream_name = f"'{self.stream_name}'"

        return (self.id, gold, self.msg_count, self.gambles,
                self.gambles_won, self.button_press,
                self.monsters, self.kills, self.exp,
                self.locations.raw, self.c_location.value,
                self._deaths, weapon, int(self.c_floor),
                int(self.is_streamer), stream_name)

    def timer_expired(self, cooldown: Cooldown) -> bool:
        """Checks if a specific timer is off of cooldown."""
        time_diff = datetime.now() - self.cooldown(cooldown)

        if cooldown == Cooldown.GOLD and time_diff < timedelta(seconds=15):
            return False
        if cooldown == Cooldown.POWERHOUR and time_diff < timedelta(hours=1):
            return False
        if cooldown == Cooldown.TAUNT and time_diff < timedelta(minutes=12):
            return False
        if cooldown == Cooldown.FORAGE and time_diff < timedelta(minutes=5):
            return False
        if cooldown == Cooldown.MINING and time_diff < timedelta(minutes=6):
            return False
        return True

    @property
    def is_powerhour(self) -> bool:
        """Checks if the user is in powerhour or not."""
        return not self.timer_expired(Cooldown.POWERHOUR)

    @property
    def in_combat(self) -> bool:
        """Checks if the user is in combat or not."""
        return self._in_combat

    def durability_loss(self, value: int) -> None:
        """Removes durability from weapons/armor."""
        if not self.weapon:
            return

        self.weapon.remove_use(value)

        # Destroy the weapon if the uses are now 0.
        if self.weapon.uses == 0:
            ItemManager.remove(self.weapon.id)
            self.weapon = None

    def set_combat(self, value: bool) -> None:
        """Set the user to be in combat."""
        self._in_combat = value

    def cooldown(self, cooldown: Cooldown) -> datetime:
        """Obtains a cooldown's status."""
        cd_timer = self._cooldowns.get(cooldown)
        if not cd_timer:
            cd_timer = datetime.now() - timedelta(hours=6)
            self._cooldowns[cooldown] = cd_timer
        return cd_timer

    def mark_cooldown(self, cooldown: Cooldown) -> None:
        """Sets the cooldown to the current time."""
        self._cooldowns[cooldown] = datetime.now()

    @property
    def gold(self) -> int:
        """Displays the current amount of gold a user has. If the user is the
        bot, it does additional calculations to determine gold amount.
        """
        if not self.is_bot:
            # Non-bot defaults to its gold amount.
            return int(self._gold)

        total: int = 0
        # Get the amount of "lost" gold for each user and add it up.
        for user in Manager.get_all():
            if user.is_bot or user._gold >= user.msg_count or user._gold < 0:
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
        """Setter for accessing protected death property."""
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
        if Manager.db:
            Manager.db.update(self.raw)

    def change_location(self, destination: Area,
                        level: Level) -> Optional[Floor]:
        """Attempts to change the user's location."""
        dungeon_floor = LocationsManager.get(destination, level)
        if not dungeon_floor:
            return None

        new_loc: Optional[Area] = None
        for area in Area:
            if not self.locations.is_unlocked(area) or not area.name:
                continue
            if area == destination:
                new_loc = area
                break

        if not new_loc:
            return None

        self.c_location = new_loc
        self.c_floor = level
        return dungeon_floor

    def apply_loot(self, loot: list[Item],
                   allow_area: bool,
                   gold_only: bool) -> Optional[Area]:
        """Applies various items to the user. If a new area is unlocked, it will
        return the new area.
        """
        new_area: Optional[Area] = None
        loot = [loot for loot in loot if loot.type != Items.NONE]
        if len(loot) == 0:
            return

        for item in loot:
            if item.type == Items.GOLD:
                self.gold += item.value
            elif item.type == Items.CHEST and isinstance(item, Chest):
                self.apply_loot(item.items, allow_area, gold_only)
            elif gold_only:
                continue
            elif item.type == Items.LOCATION and allow_area:
                # Get all connections, removing the ones already discovered.
                conn = self.locations.connections(self.c_location)
                conn = [
                    loc for loc in conn if not self.locations.is_unlocked(loc)]
                if len(conn) == 0:
                    continue

                new_area = conn[random.randrange(0, len(conn))]
                self.locations.unlock(new_area)
            else:
                self.backpack.add_item(item)
        self.backpack.save()
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
        if self.is_bot:
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
        if self.is_bot:
            return 0.0
        return max(math.log(self.level / 6, 400) + 1, 1.0)

    def add_message(self, multiplier: float = 1.0) -> None:
        """Adds a message to the user. Rewards with gold if off cooldown."""
        self.msg_count += 1

        if self.is_powerhour:
            multiplier += self.gold_multiplier_powerhour

        # Check if adding gold is off of cooldown.
        if not self.timer_expired(Cooldown.GOLD):
            return

        # Gold is not on cooldown, add.
        total_multiplier = self.gold_multiplier
        if multiplier >= 1.0:
            total_multiplier += (multiplier - 1)
        self.gold = self._gold + (1 * total_multiplier)
        self.mark_cooldown(Cooldown.GOLD)

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


class Manager:
    """Manages the User database in memory and in storage."""
    db: Optional[UserDb] = None
    _users: dict[int, User] = {}

    @staticmethod
    def init(dbname: str) -> None:
        """Initializes the User Manager, connecting and loading from
        database.
        """
        Manager.db = UserDb(dbname)
        raw_users = Manager.db.find_all()
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
    def get_all() -> list[User]:
        """Gets all the users being managed."""
        return list(Manager._users.values())
