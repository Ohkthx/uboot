"""Represents a unique creature. These files are used to customize individual
aspects for various creatures.
"""
from managers import entities
from managers.locations import Area
from managers.loot_tables import LootTable, LootPacks


class Alligator(entities.Entity):
    """Represents a type of entity."""

    def __init__(self, location: Area, difficulty: float) -> None:
        super().__init__(location, min(difficulty, 1.0))

        self.set_name("an Alligator")
        self.set_health(46, 60)
        self.image = "alligator_alive.png"

        # Add the lootpack.
        self.lootpack = LootTable.lootpack(LootPacks.UNCOMMON, self.isparagon)


def setup(manager: entities.Manager):
    """Used for loading the spawn dynamically."""
    areas = [(Area.SEWERS, 2)]
    manager.register(areas, Alligator, "alligator")
