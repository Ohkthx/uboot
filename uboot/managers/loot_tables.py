"""Handles everything from creating items to generating loot tables."""

import random
from enum import IntEnum, auto


class Items(IntEnum):
    """Represents all of the item types that can exist."""
    NONE = auto()
    GOLD = auto()
    POWERHOUR = auto()
    LOCATION = auto()


class LootPacks(IntEnum):
    """Tiers that a lootpack can be."""
    COMMON = auto()
    UNCOMMON = auto()
    RARE = auto()
    EPIC = auto()
    LEGENDARY = auto()


class Item():
    """Represents an item for a loot table, can have varying amounts."""

    def __init__(self, item_type: Items,
                 min_count: int = 1,
                 max_count: int = 1):
        # Ensure the min is the smallest value.
        if min_count > max_count:
            min_count, max_count = max_count, min_count

        self.type = item_type
        self.min = min_count
        self.max = max_count
        self.amount = 0

    @property
    def name(self) -> str:
        """Gets the name of the item based on its type."""
        if not self.type.name:
            return 'Unknown'
        return self.type.name.title()

    def generate_amount(self) -> None:
        """Get the amount of loot that will be looted."""
        self.amount = random.randint(self.min, self.max)


class LootTable():
    """Represents a loot table, used to generate loot."""

    def __init__(self, max_loot: int) -> None:
        self.max_loot = max_loot
        self.items: list[tuple[int, Item]] = []

    @staticmethod
    def lootpack(lootpack: LootPacks, upgrade: bool):
        """Gets loot based on the provided lootpack definition."""
        if upgrade and lootpack < LootPacks.LEGENDARY:
            lootpack = LootPacks(lootpack + 1)

        if lootpack == LootPacks.COMMON:
            common = CommonLoot()
            return common
        if lootpack == LootPacks.UNCOMMON:
            return UncommonLoot()
        if lootpack == LootPacks.RARE:
            return RareLoot()
        if lootpack == LootPacks.EPIC:
            return EpicLoot()
        if lootpack == LootPacks.LEGENDARY:
            return LegendaryLoot()
        return UncommonLoot()

    def add_item(self, item: Item, weight: int) -> None:
        """Adds an item to the loot table."""
        self.items.append((weight, item))

    def get_loot(self) -> list[Item]:
        """Gets loot from the loot table."""
        # Sort the list.
        self.items.sort(key=lambda i: i[0])

        # Build the lists.
        weights = [item[0] for item in self.items]
        items = [item[1] for item in self.items]

        # Create the loot, preventing duplicates except null spaces.
        loot: list[Item] = []
        max_attempts = 20
        attempts: int = 0
        while len(loot) < self.max_loot:
            if attempts > max_attempts:
                break
            attempts += 1

            item = random.choices(items, weights=weights, k=1)
            if len(item) == 0:
                break

            # Keep empty loot.
            if item[0].type == Items.NONE:
                loot.append(item[0])
                continue

            # If the item already exists, we will ignore it.
            exists: bool = False
            for i in loot:
                if i.type == item[0].type:
                    exists = True
                    break

            if not exists:
                item[0].generate_amount()
                loot.append(item[0])

        # Organize the loot.
        loot.sort(key=lambda i: i.type.value)
        return loot


class CommonLoot(LootTable):
    """Common loot, nothing to write home about."""

    def __init__(self) -> None:
        super().__init__(2)
        self.add_item(Item(Items.NONE, 0, 0), 5)
        self.add_item(Item(Items.GOLD, 22, 40), 2)
        self.add_item(Item(Items.POWERHOUR), 3)
        self.add_item(Item(Items.LOCATION), 3)


class UncommonLoot(LootTable):
    """Uncommon loot, loot is meh."""

    def __init__(self) -> None:
        super().__init__(2)
        self.add_item(Item(Items.NONE, 0, 0), 5)
        self.add_item(Item(Items.GOLD, 44, 80), 2)
        self.add_item(Item(Items.POWERHOUR), 3)
        self.add_item(Item(Items.LOCATION), 3)


class RareLoot(LootTable):
    """Rare loot, finally worth keeping."""

    def __init__(self) -> None:
        super().__init__(3)
        self.add_item(Item(Items.NONE, 0, 0), 4)
        self.add_item(Item(Items.GOLD, 108, 180), 3)
        self.add_item(Item(Items.POWERHOUR), 3)
        self.add_item(Item(Items.LOCATION), 2)


class EpicLoot(LootTable):
    """Epic loot, I may never let go of this."""

    def __init__(self) -> None:
        super().__init__(3)
        self.add_item(Item(Items.NONE, 0, 0), 4)
        self.add_item(Item(Items.GOLD, 240, 375), 3)
        self.add_item(Item(Items.POWERHOUR), 3)
        self.add_item(Item(Items.LOCATION), 2)


class LegendaryLoot(LootTable):
    """Legendary loot, how did a mortal obtain this?"""

    def __init__(self) -> None:
        super().__init__(4)
        self.add_item(Item(Items.NONE, 0, 0), 4)
        self.add_item(Item(Items.GOLD, 403, 700), 3)
        self.add_item(Item(Items.POWERHOUR), 3)
        self.add_item(Item(Items.LOCATION), 2)
