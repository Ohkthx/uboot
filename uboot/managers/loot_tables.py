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
    """Represents a unique item."""

    def __init__(self, item_type: Items,
                 min_count: int = 1,
                 max_count: int = 1):
        # Ensure the min is the smallest value.
        if min_count > max_count:
            min_count, max_count = max_count, min_count

        self.type = item_type
        self.amount = random.randint(min_count, max_count)

    @property
    def name(self) -> str:
        """Gets the name of the item based on its type."""
        if not self.type.name:
            return 'Unknown'
        return self.type.name.title()


class ItemCreator():
    """Responsible for creating an item."""

    def __init__(self, item_type: Items,
                 min_count: int = 1,
                 max_count: int = 1):
        # Ensure the min is the smallest value.
        if min_count > max_count:
            min_count, max_count = max_count, min_count

        self.type = item_type
        self.min = min_count
        self.max = max_count

    @property
    def isunique(self) -> bool:
        """Checks if only 1 of the type of item is valid for looting."""
        return self.type in (Items.POWERHOUR, Items.LOCATION)

    def create(self) -> Item:
        """Creates an instance of this item."""
        return Item(self.type, self.min, self.max)


class LootTable():
    """Represents a loot table, used to generate loot."""

    def __init__(self, max_loot: int) -> None:
        self.max_loot = max_loot
        self.items: list[tuple[int, ItemCreator]] = []

    @staticmethod
    def lootpack(lootpack: LootPacks, upgrade: bool, ischest: bool = False):
        """Gets loot based on the provided lootpack definition."""
        if upgrade and lootpack < LootPacks.LEGENDARY:
            lootpack = LootPacks(lootpack + 1)

        if lootpack == LootPacks.COMMON:
            return CommonLoot(ischest)
        if lootpack == LootPacks.UNCOMMON:
            return UncommonLoot(ischest)
        if lootpack == LootPacks.RARE:
            return RareLoot(ischest)
        if lootpack == LootPacks.EPIC:
            return EpicLoot(ischest)
        if lootpack == LootPacks.LEGENDARY:
            return LegendaryLoot(ischest)
        return UncommonLoot(ischest)

    def add_item(self, item: ItemCreator, weight: int) -> None:
        """Adds an item to the loot table."""
        self.items.append((weight, item))

    def get_loot(self, ischest: bool = False) -> list[Item]:
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

            item = random.choices(items, weights=weights)
            if len(item) == 0:
                break

            # Keep empty loot.
            if item[0].type == Items.NONE:
                loot.append(item[0].create())
                continue

            # If the item already exists, we will ignore it.
            exists: bool = False
            for i in loot:
                if not ischest and i.type == item[0].type:
                    exists = True
                    break
                if ischest and i.type == item[0].type and item[0].isunique:
                    exists = True
                    break

            if not exists:
                loot.append(item[0].create())

        # Organize the loot.
        loot.sort(key=lambda i: i.type.value)
        return loot


class CommonLoot(LootTable):
    """Common loot, nothing to write home about."""

    def __init__(self, ischest: bool = False) -> None:
        items = 2
        none_mod = 1
        chest_mod = 1
        if ischest:
            items += 3
            none_mod = 0.5
            chest_mod = 10

        super().__init__(items)
        self.add_item(ItemCreator(Items.NONE, 0, 0), int(5 * none_mod))
        self.add_item(ItemCreator(Items.GOLD, 22, 40), 2 * chest_mod)
        self.add_item(ItemCreator(Items.POWERHOUR), 3)
        self.add_item(ItemCreator(Items.LOCATION), 2)


class UncommonLoot(LootTable):
    """Uncommon loot, loot is meh."""

    def __init__(self, ischest: bool = False) -> None:
        items = 2
        none_mod = 1
        chest_mod = 1
        if ischest:
            items += 3
            none_mod = 0.5
            chest_mod = 10

        super().__init__(items)
        self.add_item(ItemCreator(Items.NONE, 0, 0), int(4 * none_mod))
        self.add_item(ItemCreator(Items.GOLD, 44, 80), 2 * chest_mod)
        self.add_item(ItemCreator(Items.POWERHOUR), 3)
        self.add_item(ItemCreator(Items.LOCATION), 2)


class RareLoot(LootTable):
    """Rare loot, finally worth keeping."""

    def __init__(self, ischest: bool = False) -> None:
        items = 3
        none_mod = 1
        chest_mod = 1
        if ischest:
            items += 3
            none_mod = 0.5
            chest_mod = 10

        super().__init__(items)
        self.add_item(ItemCreator(Items.NONE, 0, 0), int(3 * none_mod))
        self.add_item(ItemCreator(Items.GOLD, 108, 180), 3 * chest_mod)
        self.add_item(ItemCreator(Items.POWERHOUR), 3)
        self.add_item(ItemCreator(Items.LOCATION), 2)


class EpicLoot(LootTable):
    """Epic loot, I may never let go of this."""

    def __init__(self, ischest: bool = False) -> None:
        items = 3
        none_mod = 1
        chest_mod = 1
        if ischest:
            items += 3
            none_mod = 0.5
            chest_mod = 10

        super().__init__(items)
        self.add_item(ItemCreator(Items.NONE, 0, 0), int(3 * none_mod))
        self.add_item(ItemCreator(Items.GOLD, 240, 375), 3 * chest_mod)
        self.add_item(ItemCreator(Items.POWERHOUR), 3)
        self.add_item(ItemCreator(Items.LOCATION), 2)


class LegendaryLoot(LootTable):
    """Legendary loot, how did a mortal obtain this?"""

    def __init__(self, ischest: bool = False) -> None:
        items = 4
        none_mod = 1
        chest_mod = 1
        if ischest:
            items += 3
            none_mod = 0.5
            chest_mod = 10

        super().__init__(items)
        self.add_item(ItemCreator(Items.NONE, 0, 0), int(3 * none_mod))
        self.add_item(ItemCreator(Items.GOLD, 403, 700), 3 * chest_mod)
        self.add_item(ItemCreator(Items.POWERHOUR), 3)
        self.add_item(ItemCreator(Items.LOCATION), 2)
