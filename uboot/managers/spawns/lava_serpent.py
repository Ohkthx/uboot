"""Represents a unique creature. These files are used to customize individual
aspects for various creatures.
"""
from managers import entities
from managers.locations import Area
from managers.loot_tables import LootTable, LootPacks


class LavaSerpent(entities.Entity):
    """Represents a type of entity."""

    def __init__(self, location: Area, difficulty: float) -> None:
        super().__init__(location, min(difficulty, 1.0))
        self.set_name("a Lava Serpent")
        self.set_health(232, 249)
        self.image = "lava_serpent_alive.png"

        # Add the lootpack.
        self.lootpack = LootTable.lootpack(LootPacks.RARE, self.isparagon)


def setup(manager: entities.Manager):
    """Used for loading the spawn dynamically."""
    areas = [(Area.FIRE, 3)]
    manager.register(areas, LavaSerpent, "lava serpent")
