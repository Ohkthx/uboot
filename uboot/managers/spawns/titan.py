"""Represents a unique creature. These files are used to customize individual
aspects for various creatures.
"""
from managers import entities
from managers.items import Rarity
from managers.locations import Area, Level
from managers.loot_tables import LootTable


class Titan(entities.Entity):
    """Represents a type of entity."""

    def __init__(self, location: Area, difficulty: float) -> None:
        super().__init__(location, min(difficulty, 1.0))
        self.set_name("a Titan")
        self.set_health(322, 351)
        self.image = "titan_alive.png"

        # Add the lootpack.
        self.lootpack = LootTable.lootpack(Rarity.RARE, self.is_paragon)

    @staticmethod
    def locations() -> list[tuple[Area, Level, int]]:
        """Returns all the locations the entity can spawn at."""
        return [
            (Area.DESPISE, Level.FOUR, 2),
        ]


def setup(manager: entities.Manager):
    """Used for loading the spawn dynamically."""
    manager.register(Titan, "titan")
