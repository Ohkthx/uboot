"""Used for creating and managing entitys."""

import os
import sys
import math
import pathlib
import random
import importlib.util
from typing import Optional, Type
from enum import Enum, auto

from .locations import Area
from .loot_tables import LootTable, Item, Rarity

creature_actions = ["was ambushed by", "was attacked by", "was approached by",
                    "is being stalked by"]

chest_actions = ["stumbles upon", "discovers", "approaches", "finds",
                 "grows suspicious of"]

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


class Types(Enum):
    """Idenfitifies the type of entity."""
    CHEST = auto()
    CREATURE = auto()
    BOSS = auto()


class Entity():
    """Represents an entity who can be combated by users."""

    def __init__(self, location: Area, difficulty: float) -> None:
        self.name = 'an Unknown'
        self._health: int = -1
        self.difficulty = difficulty

        self.isparagon = _is_paragon(difficulty)
        self.location = location
        self._max_health: int = -1

        # Create a base loot table.
        self.lootpack = LootTable.lootpack(Rarity.COMMON, self.isparagon)
        self.type = Types.CREATURE
        self.image: Optional[str] = None

    def __str__(self) -> str:
        return f"{self.name} [{self.difficulty}]: {self.location}"

    @property
    def ischest(self) -> bool:
        """Returns if the entity is a treasure chest or not."""
        return self.type == Types.CHEST

    @property
    def isboss(self) -> bool:
        """Returns if the entity is a boss or not."""
        return self.type == Types.BOSS

    def set_name(self, name: str, rarity: str = "") -> None:
        """Sets the name of the entity."""
        rarity = f" [{rarity.capitalize()}]" if rarity != "" else ""
        mod: str = " (Paragon)" if self.isparagon else ""
        self.name = f"{name}{rarity}{mod}"

    def set_health(self, min_hp: int, max_hp: int) -> None:
        """Sets the health of the entity."""
        mod: int = 2 if self.isparagon else 1
        total_mod = mod * self.difficulty
        self._health = int(random.randint(min_hp, max_hp) * total_mod)
        self._max_health = self._health

    @property
    def max_health(self) -> int:
        """Used to scale health based on the difficulty."""
        return self._max_health

    @property
    def health(self) -> int:
        """Used to scale health based on the difficulty."""
        return int(self._health)

    @health.setter
    def health(self, val) -> None:
        """Setter for accessing protected health property."""
        self._health = val
        self._health = max(self._health, 0)

    def get_exp(self, level: int) -> float:
        """Calculates expected exp based on level that is provided."""
        mod = max(math.log(level + 10, 10), 1)
        return mod * self.max_health

    def get_action(self) -> str:
        """Gets flavored text for the entitys action."""
        if self.ischest:
            return chest_actions[random.randrange(0, len(chest_actions))]
        return creature_actions[random.randrange(0, len(creature_actions))]

    def get_loot(self) -> list[Item]:
        """Gets loot from the loot table."""
        return self.lootpack.get_loot()


class Chest(Entity):
    """Represents a treasure chest that can found."""

    def __init__(self, location: Area, difficulty: float) -> None:
        super().__init__(location, min(difficulty, 1.0))

        # Get the rarity.
        packs = [Rarity.EPIC, Rarity.RARE, Rarity.UNCOMMON]
        weights = [1, 11, 13]
        pack = random.choices(packs, weights=weights)

        self.set_name("a Treasure Chest", pack[0].name)
        self.set_health(1, 1)
        self.type = Types.CHEST
        self.image = "chest.png"

        self.lootpack = LootTable.lootpack(pack[0], self.isparagon, True)

    def get_exp(self, _: int) -> float:
        """Gets the custom EXP for a treasure chest."""
        return (2 ** (self.lootpack.rarity.value - 1)) * 50


def _resolve_name(name: str) -> str:
    try:
        return importlib.util.resolve_name(name, None)
    except ImportError as exc:
        raise ValueError(f"Entity not found: {name}") from exc


class Manager():
    """Manages the spawning of entities."""
    # Area => Weight, Entity
    _areas: dict[Area, list[tuple[int, Type[Entity]]]] = {}
    _entities: dict[str, Type[Entity]] = {}
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
    def register(areas: list[AreaWeight],
                 entity: Type[Entity], name: str) -> None:
        """Used to register entites for factory use."""
        # Add to general tracked.
        Manager._entities[name.lower()] = entity

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
    def by_name(name: str) -> Optional[Type[Entity]]:
        """Attempts to find a spawn by name."""
        for ename, entity in Manager._entities.items():
            if ename == name.lower():
                return entity
        return None

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
    def check_spawn(area: Area, difficulty: float,
                    powerhour: bool) -> Optional[Entity]:
        """Check if an entity should be spawned, if so- does."""
        modifier: float = 1
        if powerhour:
            modifier *= 1.5

        if area in (Area.SEWERS, Area.DESPISE, Area.FIRE):
            modifier *= 1.5

        chest_base = 5
        chest_range = float(chest_base * modifier)

        entity_base = 10
        entity_range = float(entity_base * modifier) + chest_range

        val = random.randint(0, 100000) / 100
        if val <= chest_range:
            # Chest spawned.
            return Chest(area, difficulty)
        if val <= entity_range:
            # Creature spawned.
            return Manager.spawn(area, difficulty)
        return None
