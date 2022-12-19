"""Used for creating and managing entitys."""

import os
import sys
import pathlib
import random
import importlib.util
from typing import Optional, Type

from .locations import Area

actions = ["was ambushed", "was attacked", "was approached",
           "is being stalked"]

AreaWeight = tuple[Area, int]


def _rand_decimal() -> float:
    """Gets a random decimal from 0 to 1."""
    return random.randint(0, 100) / 100


def _is_paragon(difficulty: float) -> bool:
    """Calculates if it is a paragon based on the difficulty of the
    creature. By default, it has a minimum of a 2% chance.
    """
    val = max(difficulty * 10 / 3, 2) / 100
    return val >= _rand_decimal()


class Entity():
    """Represents an entity who can be combated by users."""

    def __init__(self, location: Area, difficulty: float) -> None:
        self.name = 'an Unknown'
        self._health = 0
        self.difficulty = difficulty

        self.isparagon = _is_paragon(difficulty)
        self.location = location

    def set_name(self, name: str) -> None:
        """Sets the name of the entity."""
        mod: str = " (Paragon)" if self.isparagon else ""
        self.name = f"{name}{mod}"

    def set_health(self, min_hp: int, max_hp: int) -> None:
        """Sets the health of the entity."""
        mod: int = 2 if self.isparagon else 1
        self._health = random.randint(min_hp, max_hp) * mod

    @property
    def health(self) -> int:
        """Used to scale health based on the difficulty."""
        return int(self._health * self.difficulty)

    def get_action(self) -> str:
        """Gets flavored text for the entitys action."""
        return actions[random.randrange(0, len(actions))]


def _resolve_name(name: str) -> str:
    try:
        return importlib.util.resolve_name(name, None)
    except ImportError as exc:
        raise ValueError(f"Entity not found: {name}") from exc


class Manager():
    """Manages the spawning of entities."""
    # Area => Weight, Entity
    _areas: dict[Area, list[tuple[int, Type[Entity]]]] = {}
    _loaded: dict = {}

    @staticmethod
    def init() -> None:
        """Initialized all entities."""
        Manager.load_entities()

    @staticmethod
    def _load_entity(name: str) -> None:
        """Resolves an entity module and registers it."""
        name = _resolve_name(name)
        if name in Manager._loaded:
            return

        spec = importlib.util.find_spec(name)
        if not spec:
            return

        lib = importlib.util.module_from_spec(spec)
        sys.modules[name] = lib

        try:
            spec.loader.exec_module(lib)  # type: ignore
            setup = getattr(lib, 'setup')
            setup(Manager)
            Manager._loaded[name] = lib
        except Exception as exc:
            del sys.modules[name]
            raise ValueError("Could not execute module.") from exc

    @staticmethod
    def load_entities() -> None:
        """Loads all entities from the files."""
        dirname = os.path.dirname(__file__)
        path = pathlib.Path(os.path.join(dirname, 'spawns'))
        for item in path.iterdir():
            if not item.is_file() or item.name == "__init__.py":
                continue
            Manager._load_entity(f"managers.spawns.{item.stem}")

    @staticmethod
    def register(areas: list[AreaWeight], entity: Type[Entity]) -> None:
        """Used to register entites for factory use."""
        for area, weight in areas:
            if not Manager._areas.get(area):
                Manager._areas[area] = []

            # Make sure the entity isn't already added to the area.
            exists: bool = False
            area_spawns = Manager._areas.get(area, [])
            for spawn in area_spawns:
                if spawn[1] == entity:
                    exists = True
                    break

            if exists:
                continue

            # Add the entity to the area and sort it on the weight.
            area_spawns.append((weight, entity))
            area_spawns.sort(key=lambda a: a[0])

    @staticmethod
    def spawn(area: Area, difficulty: float) -> Optional[Entity]:
        """Spawns a random entity from an area."""
        area_spawns = Manager._areas.get(area)
        if not area_spawns or len(area_spawns) == 0:
            return None

        # Build the lists.
        weights = [spawn[0] for spawn in area_spawns]
        entities = [spawn[1] for spawn in area_spawns]

        # Get the spawn and create the entity.
        spawns = random.choices(entities, weights=weights, k=1)
        if len(spawns) == 0:
            return None
        return spawns[0](area, difficulty)

    @staticmethod
    def check_spawn(area: Area, difficulty: float) -> Optional[Entity]:
        """Check if an entity should be spawned, if so- does."""
        val = random.randrange(0, 100)
        if val == 0:
            return Manager.spawn(area, difficulty)
        return None
