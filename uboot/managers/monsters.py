"""Used for creating and managing monsters."""

import random
from typing import Optional

actions = ["was ambushed", "was attacked", "was approached",
           "is being stalked"]

MonsterBasic = tuple[str, int, int]
spawns: list[MonsterBasic] = [("a Mongbat", 4, 6), ("a Giant Rat", 4, 8),
                              ("a Slime", 15, 19),
                              ("a Headless One", 16, 30),
                              ("a Zombie", 28, 42), ("a Skeleton", 34, 48),
                              ("a Ghoul", 46, 60),
                              ("a Wraith", 46, 60), ("a Spectre", 46, 60),
                              ("an Imp", 55, 70), ("a Harpy", 58, 72),
                              ("an Orc", 58, 72), ("a Lizardman", 58, 72),
                              ("an Ettin", 82, 99), ("a Corpser", 94, 108),
                              ("an Ogre", 100, 117), ("a Lich", 103, 120),
                              ("a Troll", 106, 123),
                              ]


class Monster():
    """Represents a monster who can be combated by users."""

    def __init__(self, name: str, min_hp: int, max_hp,
                 difficulty: float) -> None:
        self.name = name
        self._health = random.randint(min_hp, max_hp)
        self.difficulty = difficulty

    @property
    def health(self) -> int:
        """Used to scale health based on the difficulty."""
        return int(self._health * self.difficulty)

    def get_action(self) -> str:
        """Gets flavored text for the monsters action."""
        return actions[random.randrange(0, len(actions))]


class Manager():
    """Manages the spawning of monsters."""

    @staticmethod
    def init() -> None:
        """Initialized all monsters."""
        return

    @staticmethod
    def check_spawn(difficulty: float) -> Optional[Monster]:
        """Check if a monster should be spawned, if so- does."""
        val = random.randrange(0, 200)
        if val == 0:
            pos = random.randrange(0, len(spawns))
            spawn = spawns[pos]
            return Monster(spawn[0], spawn[1], spawn[2], difficulty)
        return None
