"""Handles everything from creating items to generating loot tables."""

import random
from enum import IntEnum, auto
from typing import Optional

WEAPON_NAMES: list[str] = ["sword", "longsword", "bardiche", "cleaver",
                           "cutlass", "katana", "scimitar", "scythe",
                           "bone harvester",
                           "axe", "battle axe", "double axe", "hatchet",
                           "mace", "maul", "war axe", "war mace",
                           "dagger", "kryss", "pike", "spear", "war fork"]
TRASH_NAMES: list[str] = ["vase", "trinket", "necklace", "ring", "earrings",
                          "sandals", "cloth", "tunic", "gorget", "leggings",
                          "gloves", "bones", "spell scrolls", "silver",
                          "statue", "dye tub", "shield", "buckler",
                          "heater shield", "ringmail tunic",
                          "ringmail leggings", "copper ore", "shadow iron ore",
                          "agapite ore", "dull copper ore", "verite ore",
                          "valorite ore"]


def rand_name(names: list[str]) -> str:
    """Gets a random name from a list of names."""
    return names[random.randrange(0, len(names))]


class Items(IntEnum):
    """Represents all of the item types that can exist."""
    NONE = auto()
    GOLD = auto()
    POWERHOUR = auto()
    LOCATION = auto()
    WEAPON = auto()
    TRASH = auto()
    CHEST = auto()


class Rarity(IntEnum):
    """Tiers that a lootpacks and items can be."""
    COMMON = auto()
    UNCOMMON = auto()
    RARE = auto()
    EPIC = auto()
    LEGENDARY = auto()
    MYTHICAL = auto()


class Material(IntEnum):
    """Material for items."""
    NONE = auto()
    WOOD = auto()
    IRON = auto()
    DULL_COPPER = auto()
    SHADOW_IRON = auto()
    COPPER = auto()
    BRONZE = auto()
    GOLD = auto()
    AGAPITE = auto()
    VERITE = auto()
    VALORITE = auto()


ItemRaw = tuple[int, str, int, int, int, int, int]


class Item():
    """Represents a unique item."""

    def __init__(self, item_type: Items,
                 name: Optional[str] = None,
                 rarity: Rarity = Rarity.COMMON,
                 material: Material = Material.NONE,
                 value: int = 1,
                 uses: int = 1,
                 uses_max: int = 1):
        self.type = item_type
        self._name = name if name else item_type.name.title()
        self.rarity = rarity
        self.material = material
        self._value = value
        self.uses = uses
        self.uses_max = uses_max

    @property
    def name(self) -> str:
        """Gets the name of the item based on its type."""
        rarity: str = ""
        if self.material != Material.NONE:
            rarity = f"{self.material.name.title().replace('_', ' ')} "

        if not self.type.name and not self._name:
            return f'{rarity}Unknown'
        return f'{rarity}{self._name}'

    @property
    def base_value(self) -> int:
        """Base unmodified value of the item."""
        if self.type not in (Items.WEAPON, Items.POWERHOUR):
            return self._value
        if self.type == Items.POWERHOUR:
            return 20

        return 150

    @property
    def value(self) -> int:
        """Gets the value of the item based on its type."""
        base_value = self.base_value

        if self.type not in (Items.WEAPON, Items.POWERHOUR):
            return base_value
        if self.type == Items.POWERHOUR:
            return base_value * self.uses

        # 0 - 0.5
        material_mod: float = (max(self.material, Material.NONE) - 1) / 5
        uses_mod: float = max(self.uses / self.uses_max, 0)

        return int(base_value * (1 + material_mod) * uses_mod)

    @property
    def _raw(self) -> ItemRaw:
        """Gets the raw value of the item, used for database storage."""
        return (int(self.type), self._name, int(self.rarity),
                int(self.material), self._value, self.uses, self.uses_max)

    @property
    def isusable(self) -> bool:
        """Checks if the item can be used."""
        return self.type in (Items.POWERHOUR, Items.WEAPON)

    @property
    def isconsumable(self) -> bool:
        """Checks if the item can be consumed."""
        return self.type in (Items.POWERHOUR,)

    @staticmethod
    def from_raw(raw: ItemRaw) -> 'Item':
        """Creates an item from a raw value."""
        return Item(item_type=Items(raw[0]),
                    name=raw[1],
                    rarity=Rarity(raw[2]),
                    material=Material(raw[3]),
                    value=raw[4],
                    uses=raw[5],
                    uses_max=raw[6])

    def add_use(self, value: int) -> None:
        """Adds an additional use to an object."""
        if value <= 0:
            return
        self.uses = min(self.uses + value, self.uses_max)

    def remove_use(self, value: int) -> None:
        """Removes uses from an object."""
        if value <= 0:
            return
        self.uses = max(self.uses - value, 0)


class Chest(Item):
    """Represents a chest with multiple items."""

    def __init__(self, rarity: Rarity, items: list[Item]) -> None:
        super().__init__(Items.CHEST)
        self.rarity = rarity
        self.items = items

    @property
    def name(self) -> str:
        """Gets the name of the item based on its type."""
        return f"A Treasure Chest [{self.rarity.name.capitalize()}]"


class ItemCreator():
    """Responsible for creating an item."""

    def __init__(self, item_type: Items,
                 stacks: int,
                 min_count: int = 1,
                 max_count: int = 1) -> None:
        # Ensure the min is the smallest value.
        if min_count > max_count:
            min_count, max_count = max_count, min_count

        self.type = item_type
        self.stacks = stacks
        self.min = min_count
        self.max = max_count

    @property
    def isunique(self) -> bool:
        """Checks if only 1 of the type of item is valid for looting."""
        uniques = (Items.POWERHOUR, Items.LOCATION, Items.CHEST, Items.WEAPON)
        return self.type in uniques

    def generate(self) -> Item:
        """Creates an instance of this item."""
        self.stacks -= 1

        name: Optional[str] = None
        if self.type == Items.POWERHOUR:
            name = "powerhour potion"
            return Item(self.type, name=name, uses=1, uses_max=4)

        value = random.randint(self.min, self.max)
        if self.type == Items.WEAPON:
            name = rand_name(WEAPON_NAMES)
            material = Material(value)
            uses = material * 2
            return Item(self.type, name=name, material=material,
                        uses=uses, uses_max=uses)
        if self.type == Items.TRASH:
            name = rand_name(TRASH_NAMES)

        return Item(self.type, name=name, value=value)


class ChestCreator(ItemCreator):
    """Creates a chest."""

    def __init__(self, max_loot: int, rarity: Rarity) -> None:
        super().__init__(Items.CHEST, 1, 1)
        self.max_loot = max_loot
        self.rarity = rarity
        self.items: list[tuple[int, ItemCreator]] = []

    def add_item(self, item: ItemCreator, weight: int) -> None:
        """Adds an item to the loot table."""
        self.items.append((weight, item))

        # Sort the list.
        self.items.sort(key=lambda i: i[0])

    def generate(self) -> Chest:
        """Creates an instance of this item."""
        items = LootTable.generate_loot(self.items, self.max_loot)
        return Chest(self.rarity, items)


class LootTable():
    """Represents a loot table, used to generate loot."""

    def __init__(self, max_loot: int) -> None:
        self.max_loot = max_loot
        self.items: list[tuple[int, ItemCreator]] = []
        self.rarity = Rarity.COMMON

    @staticmethod
    def lootpack(lootpack: Rarity, upgrade: bool, ischest: bool = False):
        """Gets loot based on the provided lootpack definition."""
        if upgrade and lootpack < Rarity.MYTHICAL:
            lootpack = Rarity(lootpack + 1)

        if lootpack == Rarity.COMMON:
            return CommonLoot(upgrade, ischest)
        if lootpack == Rarity.UNCOMMON:
            return UncommonLoot(upgrade, ischest)
        if lootpack == Rarity.RARE:
            return RareLoot(upgrade, ischest)
        if lootpack == Rarity.EPIC:
            return EpicLoot(upgrade, ischest)
        if lootpack == Rarity.LEGENDARY:
            return LegendaryLoot(upgrade, ischest)
        if lootpack == Rarity.MYTHICAL:
            return MythicalLoot(upgrade, ischest)
        return UncommonLoot(upgrade, ischest)

    def add_item(self, item: ItemCreator, weight: int) -> None:
        """Adds an item to the loot table."""
        self.items.append((weight, item))

        # Sort the list.
        self.items.sort(key=lambda i: i[0])

    def get_loot(self) -> list[Item]:
        """Generates the loot for the lootpack instance."""
        return LootTable.generate_loot(self.items, self.max_loot)

    @staticmethod
    def generate_loot(item_tables: list[tuple[int, ItemCreator]],
                      max_loot: int) -> list[Item]:
        """Generates loot form a weighted table."""
        # Sort the list.
        item_tables.sort(key=lambda i: i[0])

        # Build the lists.
        weights = [item[0] for item in item_tables]
        items = [item[1] for item in item_tables]

        # Create the loot, preventing duplicates except null spaces.
        loot: list[Item] = []
        max_attempts = 20
        attempts: int = 0
        while len(loot) < max_loot:
            if attempts > max_attempts:
                break
            attempts += 1

            item = random.choices(items, weights=weights)
            if len(item) == 0:
                break

            # Keep empty loot.
            if item[0].type == Items.NONE and item[0].stacks != 0:
                loot.append(item[0].generate())
                continue

            # If the item already exists, we will ignore it.
            exists: bool = False
            for i in loot:
                if i.type == item[0].type and item[0].isunique:
                    exists = True
                    break

            if not exists and item[0].stacks != 0:
                loot.append(item[0].generate())

        # Organize the loot.
        loot.sort(key=lambda i: i.type.value)
        return loot


class CommonChest(ChestCreator):
    """Common chest, basic loot."""

    def __init__(self) -> None:
        super().__init__(2, Rarity.COMMON)
        self.add_item(ItemCreator(Items.NONE, -1, 0, 0), 4)
        self.add_item(ItemCreator(Items.GOLD, 2, 22, 40), 9)
        self.add_item(ItemCreator(Items.POWERHOUR, 1), 5)
        self.add_item(ItemCreator(Items.TRASH, 1, 22, 40), 1)

        worst, best = Material.WOOD, Material.DULL_COPPER
        self.add_item(ItemCreator(Items.WEAPON, 1, worst, best), 1)


class UncommonChest(ChestCreator):
    """Uncommon chest, wow so cool..."""

    def __init__(self) -> None:
        super().__init__(2, Rarity.UNCOMMON)
        self.add_item(ItemCreator(Items.NONE, -1, 0, 0), 4)
        self.add_item(ItemCreator(Items.GOLD, 2, 44, 80), 9)
        self.add_item(ItemCreator(Items.POWERHOUR, 1), 5)
        self.add_item(ItemCreator(Items.TRASH, 1, 44, 80), 1)

        worst, best = Material.IRON, Material.SHADOW_IRON
        self.add_item(ItemCreator(Items.WEAPON, 1, worst, best), 1)


class RareChest(ChestCreator):
    """Rare chest, hardly worth the time. """

    def __init__(self) -> None:
        super().__init__(2, Rarity.RARE)
        self.add_item(ItemCreator(Items.NONE, -1, 0, 0), 4)
        self.add_item(ItemCreator(Items.GOLD, 2, 108, 240), 9)
        self.add_item(ItemCreator(Items.POWERHOUR, 1), 5)
        self.add_item(ItemCreator(Items.TRASH, 1, 108, 240), 1)

        worst, best = Material.DULL_COPPER, Material.BRONZE
        self.add_item(ItemCreator(Items.WEAPON, 1, worst, best), 1)


class EpicChest(ChestCreator):
    """Epic chest, put in a little sweat, did ya?"""

    def __init__(self) -> None:
        super().__init__(3, Rarity.EPIC)
        self.add_item(ItemCreator(Items.NONE, -1, 0, 0), 4)
        self.add_item(ItemCreator(Items.GOLD, 3, 303, 580), 9)
        self.add_item(ItemCreator(Items.POWERHOUR, 1), 5)
        self.add_item(ItemCreator(Items.TRASH, 1, 303, 580), 1)

        worst, best = Material.COPPER, Material.AGAPITE
        self.add_item(ItemCreator(Items.WEAPON, 1, worst, best), 1)


class LegendaryChest(ChestCreator):
    """Legendary chest, only for the worthy."""

    def __init__(self) -> None:
        super().__init__(4, Rarity.LEGENDARY)
        self.add_item(ItemCreator(Items.NONE, -1, 0, 0), 4)
        self.add_item(ItemCreator(Items.GOLD, 4, 606, 1200), 9)
        self.add_item(ItemCreator(Items.POWERHOUR, 1), 5)
        self.add_item(ItemCreator(Items.TRASH, 1, 606, 1200), 1)

        worst, best = Material.GOLD, Material.VERITE
        self.add_item(ItemCreator(Items.WEAPON, 1, worst, best), 1)


class MythicalChest(ChestCreator):
    """Mythical chest, oh it is so grossly incandescent!"""

    def __init__(self) -> None:
        super().__init__(5, Rarity.MYTHICAL)
        self.add_item(ItemCreator(Items.NONE, -1, 0, 0), 4)
        self.add_item(ItemCreator(Items.GOLD, 5, 810, 1800), 9)
        self.add_item(ItemCreator(Items.POWERHOUR, 1), 5)
        self.add_item(ItemCreator(Items.TRASH, 1, 810, 1800), 1)

        worst, best = Material.VERITE, Material.VALORITE
        self.add_item(ItemCreator(Items.WEAPON, 1, worst, best), 1)


class CommonLoot(LootTable):
    """Common loot, nothing to write home about."""

    def __init__(self, isparagon: bool, ischest: bool = False) -> None:
        super().__init__(2)
        self.rarity = Rarity.COMMON

        self.add_item(CommonChest(), 21 if isparagon else 1)
        if ischest:
            return

        self.add_item(ItemCreator(Items.NONE, -1, 0, 0), 6)
        self.add_item(ItemCreator(Items.GOLD, 1, 22, 40), 4)
        self.add_item(ItemCreator(Items.POWERHOUR, 1), 4)
        self.add_item(ItemCreator(Items.LOCATION, 1), 3)
        self.add_item(ItemCreator(Items.TRASH, 1, 22, 40), 1)

        worst, best = Material.WOOD, Material.DULL_COPPER
        self.add_item(ItemCreator(Items.WEAPON, 1, worst, best), 1)


class UncommonLoot(LootTable):
    """Uncommon loot, loot is meh."""

    def __init__(self, isparagon: bool, ischest: bool = False) -> None:
        super().__init__(2)
        self.rarity = Rarity.UNCOMMON

        self.add_item(UncommonChest(), 21 if isparagon else 1)
        if ischest:
            return

        self.add_item(ItemCreator(Items.NONE, -1, 0, 0), 6)
        self.add_item(ItemCreator(Items.GOLD, 1, 44, 80), 4)
        self.add_item(ItemCreator(Items.POWERHOUR, 1), 4)
        self.add_item(ItemCreator(Items.LOCATION, 1), 3)
        self.add_item(ItemCreator(Items.TRASH, 1, 44, 80), 1)

        worst, best = Material.IRON, Material.SHADOW_IRON
        self.add_item(ItemCreator(Items.WEAPON, 1, worst, best), 1)


class RareLoot(LootTable):
    """Rare loot, finally worth keeping."""

    def __init__(self, isparagon: bool, ischest: bool = False) -> None:
        super().__init__(3)
        self.rarity = Rarity.RARE

        self.add_item(RareChest(), 21 if isparagon else 1)
        if ischest:
            return

        self.add_item(ItemCreator(Items.NONE, -1, 0, 0), 6)
        self.add_item(ItemCreator(Items.GOLD, 1, 108, 240), 4)
        self.add_item(ItemCreator(Items.POWERHOUR, 1), 4)
        self.add_item(ItemCreator(Items.LOCATION, 1), 3)
        self.add_item(ItemCreator(Items.TRASH, 1, 108, 240), 1)

        worst, best = Material.DULL_COPPER, Material.BRONZE
        self.add_item(ItemCreator(Items.WEAPON, 1, worst, best), 1)


class EpicLoot(LootTable):
    """Epic loot, I may never let go of this."""

    def __init__(self, isparagon: bool, ischest: bool = False) -> None:
        super().__init__(3)
        self.rarity = Rarity.EPIC

        self.add_item(EpicChest(), 21 if isparagon else 1)
        if ischest:
            return

        self.add_item(ItemCreator(Items.NONE, -1, 0, 0), 6)
        self.add_item(ItemCreator(Items.GOLD, 1, 303, 580), 4)
        self.add_item(ItemCreator(Items.POWERHOUR, 1), 4)
        self.add_item(ItemCreator(Items.LOCATION, 1), 3)
        self.add_item(ItemCreator(Items.TRASH, 1, 303, 580), 1)

        worst, best = Material.COPPER, Material.AGAPITE
        self.add_item(ItemCreator(Items.WEAPON, 1, worst, best), 1)


class LegendaryLoot(LootTable):
    """Legendary loot, how did a mortal obtain this?"""

    def __init__(self, isparagon: bool, ischest: bool = False) -> None:
        super().__init__(4)
        self.rarity = Rarity.LEGENDARY

        self.add_item(LegendaryChest(), 21 if isparagon else 1)
        if ischest:
            return

        self.add_item(ItemCreator(Items.NONE, -1, 0, 0), 6)
        self.add_item(ItemCreator(Items.GOLD, 1, 606, 1200), 4)
        self.add_item(ItemCreator(Items.POWERHOUR, 1), 4)
        self.add_item(ItemCreator(Items.LOCATION, 1), 3)
        self.add_item(ItemCreator(Items.TRASH, 1, 606, 1200), 1)

        worst, best = Material.GOLD, Material.VERITE
        self.add_item(ItemCreator(Items.WEAPON, 1, worst, best), 1)


class MythicalLoot(LootTable):
    """Mythical loot, only spoken in legend."""

    def __init__(self, isparagon: bool, ischest: bool = False) -> None:
        super().__init__(5)
        self.rarity = Rarity.MYTHICAL

        self.add_item(MythicalChest(), 21 if isparagon else 1)
        if ischest:
            return

        self.add_item(ItemCreator(Items.NONE, -1, 0, 0), 6)
        self.add_item(ItemCreator(Items.GOLD, 1, 810, 1800), 4)
        self.add_item(ItemCreator(Items.POWERHOUR, 1), 4)
        self.add_item(ItemCreator(Items.LOCATION, 1), 3)
        self.add_item(ItemCreator(Items.TRASH, 1, 810, 1800), 1)

        worst, best = Material.VERITE, Material.VALORITE
        self.add_item(ItemCreator(Items.WEAPON, 1, worst, best), 1)
