"""Represents a unique creature. These files are used to customize individual
aspects for various creatures.
"""
import random

from managers import entities
from managers.locations import Area
from managers.loot_tables import LootTable, LootPacks


class Slime(entities.Entity):
    """Represents a type of entity."""

    def __init__(self, location: Area, difficulty: float) -> None:
        super().__init__(location, min(difficulty, 1.0))

        name = "a Slime"
        if 0.05 >= random.randint(0, 100) / 100:
            name = "a JWilson"

        self.set_name(name)
        self.set_health(15, 19)
        self.image = "slime_alive.png"

        # Add the lootpack.
        self.lootpack = LootTable.lootpack(LootPacks.COMMON, self.isparagon)


def setup(manager: entities.Manager):
    """Used for loading the spawn dynamically."""
    areas = [(Area.SEWERS, 1), (Area.DESPISE, 5)]
    manager.register(areas, Slime, "slime")
