"""Represents a unique creature. These files are used to customize individual
aspects for various creatures.
"""
from managers import entities
from managers.items import Rarity
from managers.locations import Area, Level, Floor
from managers.loot_tables import LootTable


class OgreLord(entities.Entity):
    """Represents a type of entity."""

    def __init__(self, location: Floor, difficulty: float) -> None:
        super().__init__(location, difficulty)
        self.set_name("an Ogre Lord")
        self.set_health(476, 552)
        self.image = "ogre_alive.png"

        # Add the lootpack.
        self.lootpack = LootTable.lootpack(Rarity.EPIC, self.is_paragon)

    @staticmethod
    def locations() -> list[tuple[Area, Level, int]]:
        """Returns all the locations the entity can spawn at."""
        return [
            (Area.DESPISE, Level.FOUR, 2),
        ]


def setup(manager: entities.Manager):
    """Used for loading the spawn dynamically."""
    manager.register(OgreLord, "ogre lord")
