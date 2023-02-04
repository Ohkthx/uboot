"""Represents a unique creature. These files are used to customize individual
aspects for various creatures.
"""
from managers import entities
from managers.locations import Area, Level
from managers.loot_tables import LootTable, Rarity


class LavaSerpent(entities.Entity):
    """Represents a type of entity."""

    def __init__(self, location: Area, difficulty: float) -> None:
        super().__init__(location, min(difficulty, 1.0))
        self.set_name("a Lava Serpent")
        self.set_health(232, 249)
        self.image = "lava_serpent_alive.png"

        # Add the lootpack.
        self.lootpack = LootTable.lootpack(Rarity.RARE, self.is_paragon)

    @staticmethod
    def locations() -> list[tuple[Area, Level, int]]:
        """Returns all the locations the entity can spawn at."""
        return [
            (Area.FIRE, Level.ONE, 3),
            (Area.FIRE, Level.TWO, 5),
        ]


def setup(manager: entities.Manager):
    """Used for loading the spawn dynamically."""
    manager.register(LavaSerpent, "lava serpent")
