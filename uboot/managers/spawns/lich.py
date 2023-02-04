"""Represents a unique creature. These files are used to customize individual
aspects for various creatures.
"""
from managers import entities
from managers.locations import Area, Level
from managers.loot_tables import LootTable, Rarity


class Lich(entities.Entity):
    """Represents a type of entity."""

    def __init__(self, location: Area, difficulty: float) -> None:
        super().__init__(location, min(difficulty, 1.0))
        self.set_name("a Lich")
        self.set_health(103, 120)
        self.image = "lich_alive.png"

        # Add the lootpack.
        self.lootpack = LootTable.lootpack(Rarity.RARE, self.is_paragon)

    @staticmethod
    def locations() -> list[tuple[Area, Level, int]]:
        """Returns all the locations the entity can spawn at."""
        return [
            (Area.WILDERNESS, Level.ONE, 1),
            (Area.COVETOUS, Level.THREE, 5),
            (Area.DECEIT, Level.THREE, 5),
            (Area.DECEIT, Level.FOUR, 5),
            (Area.FIRE, Level.ONE, 5),
            (Area.FIRE, Level.TWO, 5),
        ]


def setup(manager: entities.Manager):
    """Used for loading the spawn dynamically."""
    manager.register(Lich, "lich")
