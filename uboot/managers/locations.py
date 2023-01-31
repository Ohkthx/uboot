"""Manages the location data for what is and is not unlocked."""
from enum import IntEnum, Flag, auto
from typing import Optional


# Be sure to add to connections.
class Area(Flag):
    """Possible unlockable locations."""
    BRITAIN_SEWERS = auto()
    WILDERNESS = auto()
    GRAVEYARD = auto()
    DESPISE = auto()
    FIRE = auto()
    ICE = auto()
    DESTARD = auto()
    COVETOUS = auto()
    DECEIT = auto()
    HYTHLOTH = auto()
    WRONG = auto()
    SHAME = auto()
    ORC_DUNGEON = auto()


class Level(IntEnum):
    """Total amount or the number of a Dungeon Floor."""
    ONE = auto()
    TWO = auto()
    THREE = auto()
    FOUR = auto()
    FIVE = auto()


# All currently accessible locations.
LOCATIONS: dict[Area, Level] = {
    Area.BRITAIN_SEWERS: Level.ONE,
    Area.WILDERNESS: Level.ONE,
    Area.GRAVEYARD: Level.ONE,
    Area.DESPISE: Level.FOUR,
    Area.FIRE: Level.TWO,
    Area.ICE: Level.THREE,
    Area.DESTARD: Level.THREE,
    Area.COVETOUS: Level.FIVE,
    Area.DECEIT: Level.FOUR,
    Area.HYTHLOTH: Level.FOUR,
    Area.WRONG: Level.TWO,
    Area.SHAME: Level.FIVE,
    Area.ORC_DUNGEON: Level.THREE,
}


class Locations():
    """Represents all of the currently unlocked locations."""

    def __init__(self, unlocks: int) -> None:
        self.unlocks: Area = Area(unlocks)

    @property
    def raw(self) -> int:
        """Gets the raw value of the currently unlocked locations."""
        return self.unlocks.value

    def unlock(self, unlock: Area) -> None:
        """Area a new location if it is not already unlocked."""
        self.unlocks |= unlock

    def toggle(self, unlock: Area) -> None:
        """Toggles on and off a new location."""
        self.unlocks ^= unlock

    def lock(self, unlock: Area) -> None:
        """Locks a location, preventing access to it."""
        self.unlocks &= ~unlock

    def is_unlocked(self, unlock: Area) -> bool:
        """Check if a specific location is unlocked."""
        return unlock in self.unlocks

    def get_unlocks(self) -> list[Area]:
        """Gets a list of all currently unlocked locations."""
        areas: list[Area] = []
        for area in Area:
            if self.is_unlocked(area) and area.name:
                areas.append(area)
        return areas

    def connections(self, location: Area) -> list[Area]:
        """Gets all possible unlockable locations from the location that is
        provided. This is for discovery.
        """
        if location == Area.BRITAIN_SEWERS:
            return [Area.WILDERNESS]
        if location == Area.WILDERNESS:
            return [Area.BRITAIN_SEWERS, Area.GRAVEYARD, Area.DESPISE]
        if location == Area.GRAVEYARD:
            return [Area.WILDERNESS, Area.DESPISE]
        if location == Area.DESPISE:
            return [Area.WILDERNESS, Area.GRAVEYARD, Area.FIRE]
        if location == Area.FIRE:
            return [Area.DESPISE]
        return [Area.WILDERNESS]

    @staticmethod
    def parse_area(area_name: str) -> Optional[Area]:
        """Attempts to parse an area from a name."""
        area_name = area_name.replace("_", " ").lower()
        found_loc: Optional[Area] = None
        for area in Area:
            if not area.name:
                continue

            check_name = area.name.replace("_", " ").lower()
            if area_name == check_name:
                found_loc = area
                break

        return found_loc if found_loc else None


class Floor():
    """A single floor inside of a dungeon."""

    def __init__(self, dungeon: 'Dungeon', level: Level) -> None:
        self.parent = dungeon
        self.level = level

    def __str__(self) -> str:
        """Overrides the string method for more accurate printing."""
        return self.name

    def __eq__(self, floor) -> bool:
        """Overrides the equivalency operator."""
        if isinstance(floor, Floor):
            return self.parent == floor.parent and self.level == floor.level
        return False

    @property
    def name(self) -> str:
        """Name of the floor"""
        if self.parent.levels <= Level.ONE:
            return self.parent.name
        return f"{self.parent.name} [level: {self.level.value}]"

    @property
    def key(self) -> str:
        """Identifier for the floor."""
        return f"{self.parent.area.value}:{self.level.value}"


class Dungeon():
    """Represents a dungeons with several floors."""

    def __init__(self, area: Area, levels: Level) -> None:
        self.area = area
        self.levels = levels

        # Create the floors.
        self._floors: dict[Level, Floor] = {}
        for level in Level:
            self._floors[level] = Floor(self, level)
            if level == levels:
                break

    def __str__(self) -> str:
        """Overrides the string method for more accurate printing."""
        return self.name

    def __eq__(self, dungeon: 'Dungeon') -> bool:
        """Overrides the equivalency operator."""
        if isinstance(dungeon, Dungeon):
            return self.area == dungeon.area and self.levels == dungeon.levels
        return False

    @property
    def name(self) -> str:
        """Name of the dungeon"""
        if not self.area.name:
            return "Unknown"

        return self.area.name.replace('_', ' ').title()

    @property
    def isdungeon(self) -> bool:
        """Check if it is an actual dungeon."""
        return self.area not in (Area.WILDERNESS, Area.GRAVEYARD)

    def get_floor(self, level: Level) -> Optional[Floor]:
        """Checks if a floor exist, if so gets it."""
        return self._floors.get(level, None)

    def get_floors(self) -> list[Floor]:
        """Gets all of the floors in numeric order."""
        floors = self._floors.values()
        return sorted(floors, key=lambda f: f.level)


class Manager():
    """Manages the locations and dungeons."""
    _locations: dict[Area, Dungeon] = {}

    @staticmethod
    def init() -> None:
        """Initialized all dungeons and floors."""
        for area, levels in LOCATIONS.items():
            Manager._locations[area] = Dungeon(area, levels)

    @staticmethod
    def get(area: Area, level: Level) -> Optional[Floor]:
        """Get a floor of a dungeon if it exists."""
        dungeon = Manager._locations.get(area)
        if not dungeon:
            return None

        return dungeon.get_floor(level)
