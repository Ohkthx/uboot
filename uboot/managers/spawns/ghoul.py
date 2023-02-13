"""Represents a unique creature. These files are used to customize individual
aspects for various creatures.
"""
from managers import entities
from managers.items import Rarity
from managers.locations import Area, Level
from managers.loot_tables import LootTable


class Ghoul(entities.Entity):
    """Represents a type of entity."""

    def __init__(self, location: Area, difficulty: float) -> None:
        super().__init__(location, min(difficulty, 1.0))
        self.set_name("a Ghoul")
        self.set_health(46, 60)
        self.image = "ghoul_alive.png"

        # Add the lootpack.
        self.lootpack = LootTable.lootpack(Rarity.COMMON, self.is_paragon)

    @staticmethod
    def locations() -> list[tuple[Area, Level, int]]:
        """Returns all the locations the entity can spawn at."""
        return [
            (Area.WILDERNESS, Level.ONE, 3),
            (Area.COVETOUS, Level.TWO, 5),
            (Area.COVETOUS, Level.THREE, 5),
            (Area.DECEIT, Level.ONE, 5),
            (Area.DECEIT, Level.TWO, 5),
            (Area.DECEIT, Level.THREE, 5),
        ]


def setup(manager: entities.Manager):
    """Used for loading the spawn dynamically."""
    manager.register(Ghoul, "ghoul")
