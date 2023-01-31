"""Represents a unique creature. These files are used to customize individual
aspects for various creatures.
"""
import random

from managers import entities
from managers.locations import Area, Level
from managers.loot_tables import LootTable, Rarity


class Wraith(entities.Entity):
    """Represents a type of entity."""

    def __init__(self, location: Area, difficulty: float) -> None:
        super().__init__(location, min(difficulty, 1.0))

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
        self.lootpack = LootTable.lootpack(Rarity.UNCOMMON, self.isparagon)

    @staticmethod
    def locations() -> list[tuple[Area, Level, int]]:
        """Returns all of the locations the entity can spawn at."""
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
