"""Represents a unique creature. These files are used to customize individual
aspects for various creatures.
"""
import random

from managers import entities
from managers.items import Rarity
from managers.locations import Area, Level, Floor
from managers.loot_tables import LootTable


class BoneMagi(entities.Entity):
    """Represents a type of entity."""

    def __init__(self, location: Floor, difficulty: float) -> None:
        super().__init__(location, difficulty)

        name = "a Bone Magi"
        if 0.5 >= random.randint(0, 100) / 100:
            name = "a Skeletal Mage"

        self.set_name(name)
        self.set_health(46, 60)
        self.image = "bone_magi_alive.png"

        # Add the lootpack.
        self.lootpack = LootTable.lootpack(Rarity.UNCOMMON, self.is_paragon)

    @staticmethod
    def locations() -> list[tuple[Area, Level, int]]:
        """Returns all the locations the entity can spawn at."""
        return [
            (Area.DECEIT, Level.TWO, 5),
            (Area.FIRE, Level.ONE, 5),
        ]


def setup(manager: entities.Manager):
    """Used for loading the spawn dynamically."""
    manager.register(BoneMagi, "bone magi")
