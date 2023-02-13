"""Represents a unique creature. These files are used to customize individual
aspects for various creatures.
"""
from managers import entities
from managers.items import Rarity
from managers.locations import Area, Level
from managers.loot_tables import LootTable


class Daemon(entities.Entity):
    """Represents a type of entity."""

    def __init__(self, location: Area, difficulty: float) -> None:
        super().__init__(location, min(difficulty, 1.0))
        self.set_name("a Daemon")
        self.set_health(301, 325)
        self.image = "daemon_alive.png"

        # Add the lootpack.
        self.lootpack = LootTable.lootpack(Rarity.EPIC, self.is_paragon)

    @staticmethod
    def locations() -> list[tuple[Area, Level, int]]:
        """Returns all the locations the entity can spawn at."""
        return [
            (Area.DESTARD, Level.TWO, 5),
            (Area.FIRE, Level.TWO, 5),
            (Area.HYTHLOTH, Level.TWO, 5),
            (Area.HYTHLOTH, Level.THREE, 5),
            (Area.HYTHLOTH, Level.FOUR, 5),
        ]


def setup(manager: entities.Manager):
    """Used for loading the spawn dynamically."""
    manager.register(Daemon, "daemon")
