"""Used for creating and managing entities."""

import importlib.util
import math
import os
import pathlib
import random
import sys
from enum import Enum, auto
from typing import Optional, Type

from .items import Item, Rarity
from .locations import Area, Floor, Level, Manager as LocationManager
from .loot_tables import LootTable

creature_actions = ["was ambushed by", "was attacked by", "was approached by",
                    "is being stalked by"]

chest_actions = ["stumbles upon", "discovers", "approaches", "finds",
                 "grows suspicious of"]

AreaWeight = tuple[Area, Level, int]


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
    """Identifies the type of entity."""
    CHEST = auto()
    CREATURE = auto()
    BOSS = auto()


class Entity:
    """Represents an entity who can be combated by users."""

    def __init__(self, location: Floor, difficulty: float) -> None:
        self.name = 'an Unknown'
        self._health: int = -1
        self.difficulty = max(difficulty, 1.0)

        self.is_paragon = _is_paragon(self.difficulty)
        self.location = location
        self._max_health: int = -1

        # Create a base loot table.
        self.lootpack = LootTable.lootpack(Rarity.COMMON, self.is_paragon)
        self.type = Types.CREATURE
        self.image: Optional[str] = None

    def __str__(self) -> str:
        return f"{self.name} [{self.difficulty}]: {self.location.name}"

    @property
    def is_chest(self) -> bool:
        """Returns if the entity is a treasure chest or not."""
        return self.type == Types.CHEST

    @property
    def is_boss(self) -> bool:
        """Returns if the entity is a boss or not."""
        return self.type == Types.BOSS

    @staticmethod
    def locations() -> list[AreaWeight]:
        """Gets all the locations an entity can spawn at."""
        return []

    def set_name(self, name: str, rarity: str = "") -> None:
        """Sets the name of the entity."""
        rarity = f" [{rarity.capitalize()}]" if rarity != "" else ""
        mod: str = " (Paragon)" if self.is_paragon else ""
        self.name = f"{name}{rarity}{mod}"

    def set_health(self, min_hp: int, max_hp: int) -> None:
        """Sets the health of the entity."""
        mod: int = 2 if self.is_paragon else 1
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
        """Gets flavored text for the entity's action."""
        if self.is_chest:
            return chest_actions[random.randrange(0, len(chest_actions))]
        return creature_actions[random.randrange(0, len(creature_actions))]

    def get_loot(self) -> list[Item]:
        """Gets loot from the loot table."""
        return self.lootpack.get_loot()


class Chest(Entity):
    """Represents a treasure chest that can found."""

    def __init__(self, location: Floor, difficulty: float) -> None:
        super().__init__(location, difficulty)

        # Get the rarity.
        packs = [Rarity.EPIC, Rarity.RARE, Rarity.UNCOMMON]
        weights = [1, 11, 13]
        pack = random.choices(packs, weights=weights)

        self.set_name("a Treasure Chest", pack[0].name)
        self.set_health(1, 1)
        self.type = Types.CHEST
        self.image = "chest.png"

        self.lootpack = LootTable.lootpack(pack[0], self.is_paragon, True)

    def get_exp(self, _: int) -> float:
        """Gets the custom EXP for a treasure chest."""
        return (2 ** (self.lootpack.rarity.value - 1)) * 50


def _resolve_name(name: str) -> str:
    try:
        return importlib.util.resolve_name(name, None)
    except ImportError as exc:
        raise ValueError(f"Entity not found: {name}") from exc


class Manager:
    """Manages the spawning of entities."""
    # Area => Weight, Entity
    _areas: dict[str, list[tuple[int, Type[Entity], str]]] = {}
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
    def register(entity: Type[Entity], name: str) -> None:
        """Used to register entities for factory use."""
        # Add to general tracked.
        Manager._entities[name.lower()] = entity

        areas = entity.locations()
        for area, level, weight in areas:
            dungeon_floor = LocationManager.get(area, level)
            if not dungeon_floor:
                continue

            if not Manager._areas.get(dungeon_floor.key):
                Manager._areas[dungeon_floor.key] = []

            # Make sure the entity isn't already added to the area.
            exists: bool = False
            area_spawns = Manager._areas.get(dungeon_floor.key, [])
            for spawn in area_spawns:
                if spawn[1] == entity:
                    exists = True
                    break

            if exists:
                continue

            # Add the entity to the area and sort it on the weight.
            area_spawns.append((weight, entity, name.lower()))
            area_spawns.sort(key=lambda a: a[0])

    @staticmethod
    def by_name(name: str) -> Optional[Type[Entity]]:
        """Attempts to find a spawn by name."""
        for entity_name, entity in Manager._entities.items():
            if entity_name == name.lower():
                return entity
        return None

    @staticmethod
    def floor_spawns(dungeon_floor: Floor) -> list[str]:
        """Gets all of the expected spawns for the specified floor."""
        spawns = Manager._areas.get(dungeon_floor.key, [])

        names: list[str] = []
        for spawn in spawns:
            names.append(spawn[2])
        return names

    @staticmethod
    def entity_locations(name: str) -> list[Floor]:
        """Gets all of the floors that an entity exists on."""
        entity = Manager._entities.get(name, None)
        if not entity:
            return []

        locations: list[Floor] = []
        for location in entity.locations():
            loc = LocationManager.get(location[0], location[1])
            if loc:
                locations.append(loc)
        return locations

    @staticmethod
    def spawn(area: Area, level: Level, difficulty: float) -> Optional[Entity]:
        """Spawns a random entity from an area."""
        dungeon_floor = LocationManager.get(area, level)
        if not dungeon_floor:
            return None

        area_spawns = Manager._areas.get(dungeon_floor.key)
        if not area_spawns or len(area_spawns) == 0:
            return None

        # Calculate the total difficulty
        difficulty = difficulty + max((dungeon_floor.difficulty - 1), 0)

        # Build the lists.
        weights = [spawn[0] for spawn in area_spawns]
        entities = [spawn[1] for spawn in area_spawns]

        # Get the spawn and create the entity.
        spawns = random.choices(entities, weights=weights, k=1)
        if len(spawns) == 0:
            return None
        return spawns[0](dungeon_floor, difficulty)

    @staticmethod
    def check_spawn(area: Area, level: Level, difficulty: float,
                    powerhour: bool, user_powerhour: bool,
                    is_taunt: bool) -> Optional[Entity]:
        """Check if an entity should be spawned, if so- does."""
        dungeon_floor = LocationManager.get(area, level)
        if not dungeon_floor:
            return None

        max_range: int = 1000

        multiplier: float = 1.5 if powerhour else 1.0
        if user_powerhour:
            multiplier += 0.5

        if dungeon_floor.parent.is_dungeon:
            multiplier *= 1.5

        # Put a hard limit on taunts
        taunt_multiplier = 2.0 if powerhour or user_powerhour else 1.0
        multiplier = taunt_multiplier if is_taunt else multiplier

        chest_base = 5 if not is_taunt else 0
        chest_range = float(chest_base * multiplier)

        entity_base = 10 if not is_taunt else int(max_range / 5)
        entity_range = float(entity_base * multiplier) + chest_range

        # Gets a decimal value.
        val = random.randint(0, max_range * 100) / 100
        if val <= chest_range:
            # Chest spawned.
            return Chest(dungeon_floor, difficulty)
        if val <= entity_range:
            # Creature spawned.
            return Manager.spawn(area, level, difficulty)
        return None
