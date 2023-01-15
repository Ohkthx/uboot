"""Represents a unique creature. These files are used to customize individual
aspects for various creatures.
"""
from managers import entities
from managers.locations import Area
from managers.loot_tables import LootTable, Rarity


class Daemon(entities.Entity):
    """Represents a type of entity."""

    def __init__(self, location: Area, difficulty: float) -> None:
        super().__init__(location, min(difficulty, 1.0))
        self.set_name("a Daemon")
        self.set_health(301, 325)
        self.image = "daemon_alive.png"

        # Add the lootpack.
        self.lootpack = LootTable.lootpack(Rarity.EPIC, self.isparagon)


def setup(manager: entities.Manager):
    """Used for loading the spawn dynamically."""
    areas = [(Area.FIRE, 1)]
    manager.register(areas, Daemon, "daemon")
