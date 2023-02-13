"""Represents a unique creature. These files are used to customize individual
aspects for various creatures.
"""
from managers import entities
from managers.items import Rarity
from managers.locations import Area, Level
from managers.loot_tables import LootTable


class Orc(entities.Entity):
    """Represents a type of entity."""

    def __init__(self, location: Area, difficulty: float) -> None:
        super().__init__(location, min(difficulty, 1.0))
        self.set_name("an Orc")
        self.set_health(58, 72)
        self.image = "orc_alive.png"

        # Add the lootpack.
        self.lootpack = LootTable.lootpack(Rarity.UNCOMMON, self.is_paragon)

    @staticmethod
    def locations() -> list[tuple[Area, Level, int]]:
        """Returns all the locations the entity can spawn at."""
        return [
            (Area.WILDERNESS, Level.ONE, 3),
            (Area.ORC_DUNGEON, Level.ONE, 5),
            (Area.ORC_DUNGEON, Level.TWO, 5),
            (Area.ORC_DUNGEON, Level.THREE, 5),
        ]


def setup(manager: entities.Manager):
    """Used for loading the spawn dynamically."""
    manager.register(Orc, "orc")
