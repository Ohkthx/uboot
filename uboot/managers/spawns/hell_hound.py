"""Represents a unique creature. These files are used to customize individual
aspects for various creatures.
"""
from managers import entities
from managers.items import Rarity
from managers.locations import Area, Level, Floor
from managers.loot_tables import LootTable


class HellHound(entities.Entity):
    """Represents a type of entity."""

    def __init__(self, location: Floor, difficulty: float) -> None:
        super().__init__(location, difficulty)
        self.set_name("a Hell Hound")
        self.set_health(66, 125)

        # Add the lootpack.
        self.lootpack = LootTable.lootpack(Rarity.UNCOMMON, self.is_paragon)

    @staticmethod
    def locations() -> list[tuple[Area, Level, int]]:
        """Returns all the locations the entity can spawn at."""
        return [
            (Area.FIRE, Level.ONE, 4),
            (Area.FIRE, Level.TWO, 5),
            (Area.HYTHLOTH, Level.ONE, 5),
            (Area.HYTHLOTH, Level.TWO, 5),
            (Area.HYTHLOTH, Level.THREE, 5),
            (Area.HYTHLOTH, Level.FOUR, 5),
        ]


def setup(manager: entities.Manager):
    """Used for loading the spawn dynamically."""
    manager.register(HellHound, "hell hound")
