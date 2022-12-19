"""Represents a unique creature. These files are used to customize individual
aspects for various creatures.
"""
import random

from managers import entities
from managers.locations import Area


class Wraith(entities.Entity):
    """Represents a type of entity."""

    def __init__(self, location: Area, difficulty: float) -> None:
        super().__init__(location, min(difficulty, 1.0))

        name = "a Wraith"
        if 0.5 >= random.randint(0, 100) / 100:
            name = "a Spectre"

        self.set_name(name)
        self.set_health(46, 60)


def setup(manager: entities.Manager):
    """Used for loading the spawn dynamically."""
    areas = [(Area.GRAVEYARD, 3)]
    manager.register(areas, Wraith)
