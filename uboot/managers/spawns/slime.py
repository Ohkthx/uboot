"""Represents a unique creature. These files are used to customize individual
aspects for various creatures.
"""
import random

from managers import entities
from managers.locations import Area, Level
from managers.loot_tables import LootTable, Rarity


class Slime(entities.Entity):
    """Represents a type of entity."""

    def __init__(self, location: Area, difficulty: float) -> None:
        super().__init__(location, min(difficulty, 1.0))

        name = "a Slime"
        if 0.05 >= random.randint(0, 100) / 100:
            name = "a JWilson"

        self.set_name(name)
        self.set_health(15, 19)
        self.image = "slime_alive.png"

        # Add the lootpack.
        self.lootpack = LootTable.lootpack(Rarity.COMMON, self.isparagon)

    @staticmethod
    def locations() -> list[tuple[Area, Level, int]]:
        """Returns all of the locations the entity can spawn at."""
        return [
            (Area.BRITAIN_SEWERS, Level.ONE, 1),
            (Area.DESPISE, Level.FOUR, 3),
            (Area.FIRE, Level.ONE, 5),
        ]


def setup(manager: entities.Manager):
    """Used for loading the spawn dynamically."""
    manager.register(Slime, "slime")
