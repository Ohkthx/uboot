"""Represents a unique creature. These files are used to customize individual
aspects for various creatures.
"""
from managers import entities
from managers.locations import Area


class Skeleton(entities.Entity):
    """Represents a type of entity."""

    def __init__(self, location: Area, difficulty: float) -> None:
        super().__init__(location, min(difficulty, 1.0))
        self.set_name("a Skeleton")
        self.set_health(34, 48)


def setup(manager: entities.Manager):
    """Used for loading the spawn dynamically."""
    areas = [(Area.WILDERNESS, 3), (Area.GRAVEYARD, 7)]
    manager.register(areas, Skeleton)
