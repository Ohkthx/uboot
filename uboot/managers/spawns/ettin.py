"""Represents a unique creature. These files are used to customize individual
aspects for various creatures.
"""
from managers import entities
from managers.locations import Area


class Ettin(entities.Entity):
    """Represents a type of entity."""

    def __init__(self, location: Area, difficulty: float) -> None:
        super().__init__(location, min(difficulty, 1.0))
        self.set_name("an Ettin")
        self.set_health(82, 99)


def setup(manager: entities.Manager):
    """Used for loading the spawn dynamically."""
    areas = [(Area.WILDERNESS, 4), (Area.DESPISE, 6)]
    manager.register(areas, Ettin)
