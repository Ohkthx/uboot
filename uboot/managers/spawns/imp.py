"""Represents a unique creature. These files are used to customize individual
aspects for various creatures.
"""
from managers import entities
from managers.locations import Area, Level
from managers.loot_tables import LootTable, Rarity


class Imp(entities.Entity):
    """Represents a type of entity."""

    def __init__(self, location: Area, difficulty: float) -> None:
        super().__init__(location, min(difficulty, 1.0))
        self.set_name("an Imp")
        self.set_health(55, 70)

        # Add the lootpack.
        self.lootpack = LootTable.lootpack(Rarity.UNCOMMON, self.isparagon)
        self.image = "imp_alive.png"

    @staticmethod
    def locations() -> list[tuple[Area, Level, int]]:
        """Returns all of the locations the entity can spawn at."""
        return [
            (Area.WILDERNESS, Level.ONE, 1),
            (Area.HYTHLOTH, Level.ONE, 5),
            (Area.HYTHLOTH, Level.TWO, 5),
            (Area.HYTHLOTH, Level.THREE, 5),
            (Area.HYTHLOTH, Level.FOUR, 5),
        ]


def setup(manager: entities.Manager):
    """Used for loading the spawn dynamically."""
    manager.register(Imp, "imp")
