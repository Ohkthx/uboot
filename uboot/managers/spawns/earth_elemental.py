"""Represents a unique creature. These files are used to customize individual
aspects for various creatures.
"""
from managers import entities
from managers.locations import Area


class EarthElemental(entities.Entity):
    """Represents a type of entity."""

    def __init__(self, location: Area, difficulty: float) -> None:
        super().__init__(location, min(difficulty, 1.0))
        self.set_name("an Earth Elemental")
        self.set_health(76, 93)


def setup(manager: entities.Manager):
    """Used for loading the spawn dynamically."""
    areas = [(Area.DESPISE, 5)]
    manager.register(areas, EarthElemental)
