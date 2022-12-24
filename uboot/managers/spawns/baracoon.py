"""Represents a unique creature. These files are used to customize individual
aspects for various creatures.
"""
from managers import entities
from managers.locations import Area
from managers.loot_tables import LootTable, LootPacks


class BaracoonThePiper(entities.Entity):
    """Represents a type of entity."""

    def __init__(self, location: Area, difficulty: float) -> None:
        super().__init__(location, min(difficulty, 1.0))
        self.set_name("Baracoon the Piper")
        self.set_health(12000, 12000)

        # Add the lootpack.
        self.lootpack = LootTable.lootpack(LootPacks.MYTHICAL, self.isparagon)


def setup(manager: entities.Manager):
    """Used for loading the spawn dynamically."""
    areas = [(Area(0), 1)]
    manager.register(areas, BaracoonThePiper, "baracoon")
