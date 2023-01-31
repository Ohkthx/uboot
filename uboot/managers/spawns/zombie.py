"""Represents a unique creature. These files are used to customize individual
aspects for various creatures.
"""
from managers import entities
from managers.locations import Area, Level
from managers.loot_tables import LootTable, Rarity


class Zombie(entities.Entity):
    """Represents a type of entity."""

    def __init__(self, location: Area, difficulty: float) -> None:
        super().__init__(location, min(difficulty, 1.0))
        self.set_name("a Zombie")
        self.set_health(28, 42)
        self.image = "zombie_alive.png"

        # Add the lootpack.
        self.lootpack = LootTable.lootpack(Rarity.COMMON, self.isparagon)

    @staticmethod
    def locations() -> list[tuple[Area, Level, int]]:
        """Returns all of the locations the entity can spawn at."""
        return [
            (Area.WILDERNESS, Level.ONE, 3),
            (Area.GRAVEYARD, Level.ONE, 7),
            (Area.COVETOUS, Level.THREE, 5),
            (Area.COVETOUS, Level.FOUR, 5),
            (Area.DECEIT, Level.TWO, 5),
        ]


def setup(manager: entities.Manager):
    """Used for loading the spawn dynamically."""
    manager.register(Zombie, "zombie")
