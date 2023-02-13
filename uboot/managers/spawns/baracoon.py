"""Represents a unique creature. These files are used to customize individual
aspects for various creatures.
"""
from managers import entities
from managers.items import Rarity
from managers.locations import Area, Level
from managers.loot_tables import LootTable


class BaracoonThePiper(entities.Entity):
    """Represents a type of entity."""

    def __init__(self, location: Area, difficulty: float) -> None:
        super().__init__(location, min(difficulty, 1.0))
        self.set_name("Baracoon the Piper")
        self.set_health(12000, 12000)

        # Add the lootpack.
        self.lootpack = LootTable.lootpack(Rarity.MYTHICAL, self.is_paragon)

    @staticmethod
    def locations() -> list[tuple[Area, Level, int]]:
        """Returns all the locations the entity can spawn at."""
        return [
            (Area(0), Level.ONE, 1),
        ]


def setup(manager: entities.Manager):
    """Used for loading the spawn dynamically."""
    manager.register(BaracoonThePiper, "baracoon")
