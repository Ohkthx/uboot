"""Represents a unique creature. These files are used to customize individual
aspects for various creatures.
"""
from managers import entities
from managers.locations import Area, Level
from managers.loot_tables import LootTable, Rarity


class Troll(entities.Entity):
    """Represents a type of entity."""

    def __init__(self, location: Area, difficulty: float) -> None:
        super().__init__(location, min(difficulty, 1.0))
        self.set_name("a Troll")
        self.set_health(106, 123)
        self.image = "troll_alive.png"

        # Add the lootpack.
        self.lootpack = LootTable.lootpack(Rarity.UNCOMMON, self.isparagon)

    @staticmethod
    def locations() -> list[tuple[Area, Level, int]]:
        """Returns all of the locations the entity can spawn at."""
        return [
            (Area.WILDERNESS, Level.ONE, 2),
            (Area.DESPISE, Level.FOUR, 5),
        ]


def setup(manager: entities.Manager):
    """Used for loading the spawn dynamically."""
    manager.register(Troll, "troll")
