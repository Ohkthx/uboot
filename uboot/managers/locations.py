"""Manages the location data for what is and is not unlocked."""
from enum import Flag, auto


# Be sure to add to connections.
class Area(Flag):
    """Possible unlockable locations."""
    SEWERS = auto()
    WILDERNESS = auto()
    GRAVEYARD = auto()
    DESPISE = auto()


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

    def get_unlocks(self) -> list[str]:
        """Gets a list of all currently unlocked locations."""
        areas: list[str] = []
        for area in Area:
            if self.is_unlocked(area) and area.name:
                areas.append(area.name.lower())
        return areas

    def connections(self, location: Area) -> list[Area]:
        """Gets all possible unlockable locations from the location that is
        provided. This is for discovery.
        """
        if location == Area.SEWERS:
            return [Area.WILDERNESS]
        if location == Area.WILDERNESS:
            return [Area.GRAVEYARD, Area.DESPISE]
        if location == Area.GRAVEYARD:
            return [Area.WILDERNESS, Area.DESPISE]
        if location == Area.DESPISE:
            return [Area.WILDERNESS, Area.GRAVEYARD]
        return [Area.WILDERNESS]
