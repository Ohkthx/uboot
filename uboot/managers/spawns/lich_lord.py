"""Represents a unique creature. These files are used to customize individual
aspects for various creatures.
"""
from managers import entities
from managers.items import Rarity
from managers.locations import Area, Level, Floor
from managers.loot_tables import LootTable


class LichLord(entities.Entity):
    """Represents a type of entity."""

    def __init__(self, location: Floor, difficulty: float) -> None:
        super().__init__(location, difficulty)
        self.set_name("a Lich Lord")
        self.set_health(250, 303)
        self.image = "lich_lord_alive.png"

        # Add the lootpack.
        self.lootpack = LootTable.lootpack(Rarity.RARE, self.is_paragon)

    @staticmethod
    def locations() -> list[tuple[Area, Level, int]]:
        """Returns all the locations the entity can spawn at."""
        return [
            (Area.COVETOUS, Level.THREE, 5),
            (Area.DECEIT, Level.FOUR, 5),
            (Area.FIRE, Level.ONE, 3),
            (Area.FIRE, Level.TWO, 5),
        ]


def setup(manager: entities.Manager):
    """Used for loading the spawn dynamically."""
    manager.register(LichLord, "lich lord")
