"""Represents a unique creature. These files are used to customize individual
aspects for various creatures.
"""
from managers import entities
from managers.items import Rarity
from managers.locations import Area, Level, Floor
from managers.loot_tables import LootTable


class EarthElemental(entities.Entity):
    """Represents a type of entity."""

    def __init__(self, location: Floor, difficulty: float) -> None:
        super().__init__(location, difficulty)
        self.set_name("an Earth Elemental")
        self.set_health(76, 93)
        self.image = "earth_elemental_alive.png"

        # Add the lootpack.
        self.lootpack = LootTable.lootpack(Rarity.UNCOMMON, self.is_paragon)

    @staticmethod
    def locations() -> list[tuple[Area, Level, int]]:
        """Returns all the locations the entity can spawn at."""
        return [
            (Area.DESPISE, Level.TWO, 5),
            (Area.ORC_DUNGEON, Level.THREE, 5),
            (Area.SHAME, Level.ONE, 5),
            (Area.SHAME, Level.TWO, 5),
            (Area.SHAME, Level.THREE, 5),
            (Area.SHAME, Level.FOUR, 5),
            (Area.SHAME, Level.FIVE, 5),
        ]


def setup(manager: entities.Manager):
    """Used for loading the spawn dynamically."""
    manager.register(EarthElemental, "earth elemental")
