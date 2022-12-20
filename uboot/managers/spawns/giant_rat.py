"""Represents a unique creature. These files are used to customize individual
aspects for various creatures.
"""
from managers import entities
from managers.locations import Area
from managers.loot_tables import LootTable, LootPacks


class GiantRat(entities.Entity):
    """Represents a type of entity."""

    def __init__(self, location: Area, difficulty: float) -> None:
        super().__init__(location, min(difficulty, 1.0))
        self.set_name("a Giant Rat")
        self.set_health(26, 39)

        # Add the lootpack.
        self.lootpack = LootTable.lootpack(LootPacks.COMMON, self.isparagon)


def setup(manager: entities.Manager):
    """Used for loading the spawn dynamically."""
    areas = [(Area.SEWERS, 5), (Area.WILDERNESS, 4)]
    manager.register(areas, GiantRat)
