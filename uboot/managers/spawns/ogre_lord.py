"""Represents a unique creature. These files are used to customize individual
aspects for various creatures.
"""
from managers import entities
from managers.locations import Area
from managers.loot_tables import LootTable, LootPacks


class OgreLord(entities.Entity):
    """Represents a type of entity."""

    def __init__(self, location: Area, difficulty: float) -> None:
        super().__init__(location, min(difficulty, 1.0))
        self.set_name("an Ogre Lord")
        self.set_health(476, 552)

        # Add the lootpack.
        self.lootpack = LootTable.lootpack(LootPacks.EPIC, self.isparagon)


def setup(manager: entities.Manager):
    """Used for loading the spawn dynamically."""
    areas = [(Area.DESPISE, 1)]
    manager.register(areas, OgreLord)
