"""Represents a unique creature. These files are used to customize individual
aspects for various creatures.
"""
import random

from managers import entities
from managers.items import Rarity
from managers.locations import Area, Level, Floor
from managers.loot_tables import LootTable


class Wraith(entities.Entity):
    """Represents a type of entity."""

    def __init__(self, location: Floor, difficulty: float) -> None:
        super().__init__(location, difficulty)

        name = "a Wraith"
        roll = random.randint(0, 100) / 100
        if roll <= 0.33:
            name = "a Spectre"
        elif roll <= 0.66:
            name = "a Shade"

        self.set_name(name)
        self.set_health(46, 60)
        self.image = "wraith_alive.png"

        # Add the lootpack.
        self.lootpack = LootTable.lootpack(Rarity.UNCOMMON, self.is_paragon)

    @staticmethod
    def locations() -> list[tuple[Area, Level, int]]:
        """Returns all the locations the entity can spawn at."""
        return [
            (Area.GRAVEYARD, Level.ONE, 3),
            (Area.COVETOUS, Level.THREE, 5),
            (Area.COVETOUS, Level.FOUR, 5),
            (Area.DECEIT, Level.ONE, 5),
            (Area.DECEIT, Level.TWO, 5),
            (Area.DECEIT, Level.THREE, 5),
        ]


def setup(manager: entities.Manager):
    """Used for loading the spawn dynamically."""
    manager.register(Wraith, "wraith")
