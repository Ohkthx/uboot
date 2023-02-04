"""Represents a unique creature. These files are used to customize individual
aspects for various creatures.
"""
import random

from managers import entities
from managers.locations import Area, Level
from managers.loot_tables import LootTable, Rarity


class Rat(entities.Entity):
    """Represents a type of entity."""

    def __init__(self, location: Area, difficulty: float) -> None:
        super().__init__(location, min(difficulty, 1.0))

        name = "a Rat"
        if 0.5 >= random.randint(0, 100) / 100:
            name = "a Sewer Rat"

        self.set_name(name)
        self.set_health(6, 6)
        self.image = "rat_alive.png"

        # Add the lootpack.
        self.lootpack = LootTable.lootpack(Rarity.COMMON, self.is_paragon)

    @staticmethod
    def locations() -> list[tuple[Area, Level, int]]:
        """Returns all the locations the entity can spawn at."""
        return [
            (Area.BRITAIN_SEWERS, Level.ONE, 8),
            (Area.WILDERNESS, Level.ONE, 1),
        ]


def setup(manager: entities.Manager):
    """Used for loading the spawn dynamically."""
    manager.register(Rat, "rat")
