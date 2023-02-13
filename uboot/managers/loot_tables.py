"""Handles everything from creating items to generating loot tables."""

import random
from typing import Optional
import uuid

from .items import Item, Items, Material, Rarity, Chest

WEAPON_NAMES: list[str] = ["sword", "longsword", "bardiche", "cleaver",
                           "cutlass", "katana", "scimitar", "scythe",
                           "bone harvester",
                           "axe", "battle axe", "double axe", "hatchet",
                           "mace", "maul", "war axe", "war mace",
                           "dagger", "kryss", "pike", "spear", "war fork"]
TRASH_NAMES: list[str] = ["vase", "trinket", "necklace", "ring", "earrings",
                          "sandals", "cloth", "tunic", "gorget", "leggings",
                          "gloves", "spell scrolls", "silver",
                          "statue", "dye tub", "shield", "buckler",
                          "heater shield", "ringmail tunic",
                          "ringmail leggings"]
BAG_NAMES: list[str] = ["pouch", "bag", "wooden box", "basket",
                        "small crate", "medium crate", "large crate",
                        "decorative box", "picnic basket",
                        ]


def rand_name(names: list[str]) -> str:
    """Gets a random name from a list of names."""
    return names[random.randrange(0, len(names))]


class ItemCreator:
    """Responsible for creating an item."""

    def __init__(self, item_type: Items,
                 stacks: int,
                 min_count: int = 1,
                 max_count: int = 1,
                 modifier: float = 1.0) -> None:
        # Ensure the min is the smallest value.
        if min_count > max_count:
            min_count, max_count = max_count, min_count

        self.type = item_type
        self.stacks = stacks
        self.min = min_count
        self.max = max_count
        self.modifier = modifier

    @property
    def is_unique(self) -> bool:
        """Checks if only 1 of the type of item is valid for looting."""
        uniques = (Items.POWERHOUR, Items.LOCATION,
                   Items.CHEST, Items.WEAPON, Items.BAG)
        return self.type in uniques

    def generate(self) -> Item:
        """Creates an instance of this item."""
        self.stacks -= 1
        item_id: str = str(uuid.uuid4())

        name: Optional[str] = None
        if self.type == Items.POWERHOUR:
            name = "powerhour potion"
            return Item(item_id, self.type, name=name, uses=1, uses_max=4)

        value = random.randint(self.min, self.max)
        if self.type == Items.WEAPON:
            name = rand_name(WEAPON_NAMES)
            material = Material(value)
            uses = material * 2
            return Item(item_id, self.type, name=name, material=material,
                        uses=uses, uses_max=uses)
        if self.type == Items.BAG:
            name = rand_name(BAG_NAMES)
            return Item(item_id, self.type, name=name,
                        uses=self.max,
                        uses_max=self.max)

        if self.type == Items.TRASH:
            name = rand_name(TRASH_NAMES)
            value = int(value * self.modifier)

        return Item(item_id, self.type, name=name, value=value)


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


class LootTable:
    """Represents a loot table, used to generate loot."""

    def __init__(self, max_loot: int) -> None:
        self.max_loot = max_loot
        self.items: list[tuple[int, ItemCreator]] = []
        self.rarity = Rarity.COMMON

    @staticmethod
    def lootpack(lootpack: Rarity, upgrade: bool, is_chest: bool = False):
        """Gets loot based on the provided lootpack definition."""
        if upgrade and lootpack < Rarity.MYTHICAL:
            lootpack = Rarity(lootpack + 1)

        if lootpack == Rarity.COMMON:
            return CommonLoot(upgrade, is_chest)
        if lootpack == Rarity.UNCOMMON:
            return UncommonLoot(upgrade, is_chest)
        if lootpack == Rarity.RARE:
            return RareLoot(upgrade, is_chest)
        if lootpack == Rarity.EPIC:
            return EpicLoot(upgrade, is_chest)
        if lootpack == Rarity.LEGENDARY:
            return LegendaryLoot(upgrade, is_chest)
        if lootpack == Rarity.MYTHICAL:
            return MythicalLoot(upgrade, is_chest)
        return UncommonLoot(upgrade, is_chest)

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
        item_tables.sort(key=lambda item: item[0])

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
                if i.type == item[0].type and item[0].is_unique:
                    exists = True
                    break

            if not exists and item[0].stacks != 0:
                loot.append(item[0].generate())

        # Organize the loot.
        loot.sort(key=lambda item: item.type.value)
        return loot


class CommonChest(ChestCreator):
    """Common chest, basic loot."""

    def __init__(self) -> None:
        super().__init__(2, Rarity.COMMON)
        self.add_item(ItemCreator(Items.NONE, -1, 0, 0), 20)
        self.add_item(ItemCreator(Items.GOLD, 2, 22, 40), 35)
        self.add_item(ItemCreator(Items.POWERHOUR, 1), 30)
        self.add_item(ItemCreator(Items.TRASH, 1, 22, 40), 10)

        worst, best = Material.WOOD, Material.DULL_COPPER
        self.add_item(ItemCreator(Items.WEAPON, 1, worst, best), 4)
        self.add_item(ItemCreator(Items.BAG, 1, 4, 4), 1)


class UncommonChest(ChestCreator):
    """Uncommon chest, wow so cool..."""

    def __init__(self) -> None:
        super().__init__(2, Rarity.UNCOMMON)
        self.add_item(ItemCreator(Items.NONE, -1, 0, 0), 20)
        self.add_item(ItemCreator(Items.GOLD, 2, 44, 80), 35)
        self.add_item(ItemCreator(Items.POWERHOUR, 1), 30)
        self.add_item(ItemCreator(Items.TRASH, 1, 44, 80), 10)

        worst, best = Material.IRON, Material.SHADOW_IRON
        self.add_item(ItemCreator(Items.WEAPON, 1, worst, best), 4)
        self.add_item(ItemCreator(Items.BAG, 1, 4, 4), 1)


class RareChest(ChestCreator):
    """Rare chest, hardly worth the time. """

    def __init__(self) -> None:
        super().__init__(2, Rarity.RARE)
        self.add_item(ItemCreator(Items.NONE, -1, 0, 0), 20)
        self.add_item(ItemCreator(Items.GOLD, 2, 108, 240), 35)
        self.add_item(ItemCreator(Items.POWERHOUR, 1), 30)
        self.add_item(ItemCreator(Items.TRASH, 1, 108, 240), 10)

        worst, best = Material.DULL_COPPER, Material.BRONZE
        self.add_item(ItemCreator(Items.WEAPON, 1, worst, best), 4)
        self.add_item(ItemCreator(Items.BAG, 1, 8, 8), 1)


class EpicChest(ChestCreator):
    """Epic chest, put in a little sweat, did ya?"""

    def __init__(self) -> None:
        super().__init__(3, Rarity.EPIC)
        self.add_item(ItemCreator(Items.NONE, -1, 0, 0), 10)
        self.add_item(ItemCreator(Items.GOLD, 3, 303, 580), 35)
        self.add_item(ItemCreator(Items.POWERHOUR, 1), 30)
        self.add_item(ItemCreator(Items.TRASH, 1, 303, 580), 10)

        worst, best = Material.COPPER, Material.AGAPITE
        self.add_item(ItemCreator(Items.WEAPON, 1, worst, best), 9)
        self.add_item(ItemCreator(Items.BAG, 1, 12, 12), 6)


class LegendaryChest(ChestCreator):
    """Legendary chest, only for the worthy."""

    def __init__(self) -> None:
        super().__init__(4, Rarity.LEGENDARY)
        self.add_item(ItemCreator(Items.NONE, -1, 0, 0), 10)
        self.add_item(ItemCreator(Items.GOLD, 4, 606, 1200), 35)
        self.add_item(ItemCreator(Items.POWERHOUR, 1), 30)
        self.add_item(ItemCreator(Items.TRASH, 1, 606, 1200), 10)

        worst, best = Material.GOLD, Material.VERITE
        self.add_item(ItemCreator(Items.WEAPON, 1, worst, best), 9)
        self.add_item(ItemCreator(Items.BAG, 1, 16, 16), 6)


class MythicalChest(ChestCreator):
    """Mythical chest, oh it is so grossly incandescent!"""

    def __init__(self) -> None:
        super().__init__(5, Rarity.MYTHICAL)
        self.add_item(ItemCreator(Items.NONE, -1, 0, 0), 10)
        self.add_item(ItemCreator(Items.GOLD, 5, 810, 1800), 35)
        self.add_item(ItemCreator(Items.POWERHOUR, 1), 30)
        self.add_item(ItemCreator(Items.TRASH, 1, 810, 1800), 10)

        worst, best = Material.VERITE, Material.VALORITE
        self.add_item(ItemCreator(Items.WEAPON, 1, worst, best), 9)
        self.add_item(ItemCreator(Items.BAG, 1, 16, 16), 6)


class CommonLoot(LootTable):
    """Common loot, nothing to write home about."""

    def __init__(self, is_paragon: bool, is_chest: bool = False) -> None:
        super().__init__(2)
        self.rarity = Rarity.COMMON

        self.add_item(CommonChest(), 105 if is_paragon else 5)
        if is_chest:
            return

        self.add_item(ItemCreator(Items.NONE, -1, 0, 0), 25)
        self.add_item(ItemCreator(Items.GOLD, 1, 22, 40), 20)
        self.add_item(ItemCreator(Items.POWERHOUR, 1), 15)
        self.add_item(ItemCreator(Items.LOCATION, 1), 25)
        self.add_item(ItemCreator(Items.TRASH, 1, 22, 40, 0.75), 7)

        worst, best = Material.WOOD, Material.DULL_COPPER
        self.add_item(ItemCreator(Items.WEAPON, 1, worst, best), 2)
        self.add_item(ItemCreator(Items.BAG, 1, 4, 4), 1)


class UncommonLoot(LootTable):
    """Uncommon loot, loot is meh."""

    def __init__(self, is_paragon: bool, is_chest: bool = False) -> None:
        super().__init__(2)
        self.rarity = Rarity.UNCOMMON

        self.add_item(UncommonChest(), 105 if is_paragon else 5)
        if is_chest:
            return

        self.add_item(ItemCreator(Items.NONE, -1, 0, 0), 25)
        self.add_item(ItemCreator(Items.GOLD, 1, 44, 80), 20)
        self.add_item(ItemCreator(Items.POWERHOUR, 1), 15)
        self.add_item(ItemCreator(Items.LOCATION, 1), 25)
        self.add_item(ItemCreator(Items.TRASH, 1, 44, 80, 0.75), 7)

        worst, best = Material.IRON, Material.SHADOW_IRON
        self.add_item(ItemCreator(Items.WEAPON, 1, worst, best), 2)
        self.add_item(ItemCreator(Items.BAG, 1, 4, 4), 1)


class RareLoot(LootTable):
    """Rare loot, finally worth keeping."""

    def __init__(self, is_paragon: bool, is_chest: bool = False) -> None:
        super().__init__(3)
        self.rarity = Rarity.RARE

        self.add_item(RareChest(), 105 if is_paragon else 5)
        if is_chest:
            return

        self.add_item(ItemCreator(Items.NONE, -1, 0, 0), 25)
        self.add_item(ItemCreator(Items.GOLD, 1, 108, 240), 20)
        self.add_item(ItemCreator(Items.POWERHOUR, 1), 15)
        self.add_item(ItemCreator(Items.LOCATION, 1), 25)
        self.add_item(ItemCreator(Items.TRASH, 1, 108, 240, 0.75), 7)

        worst, best = Material.DULL_COPPER, Material.BRONZE
        self.add_item(ItemCreator(Items.WEAPON, 1, worst, best), 2)
        self.add_item(ItemCreator(Items.BAG, 1, 8, 8), 1)


class EpicLoot(LootTable):
    """Epic loot, I may never let go of this."""

    def __init__(self, is_paragon: bool, is_chest: bool = False) -> None:
        super().__init__(3)
        self.rarity = Rarity.EPIC

        self.add_item(EpicChest(), 105 if is_paragon else 5)
        if is_chest:
            return

        self.add_item(ItemCreator(Items.NONE, -1, 0, 0), 23)
        self.add_item(ItemCreator(Items.GOLD, 1, 303, 580), 20)
        self.add_item(ItemCreator(Items.POWERHOUR, 1), 15)
        self.add_item(ItemCreator(Items.LOCATION, 1), 25)
        self.add_item(ItemCreator(Items.TRASH, 1, 303, 580, 0.75), 7)

        worst, best = Material.COPPER, Material.AGAPITE
        self.add_item(ItemCreator(Items.WEAPON, 1, worst, best), 3)
        self.add_item(ItemCreator(Items.BAG, 1, 12, 12), 2)


class LegendaryLoot(LootTable):
    """Legendary loot, how did a mortal obtain this?"""

    def __init__(self, is_paragon: bool, is_chest: bool = False) -> None:
        super().__init__(4)
        self.rarity = Rarity.LEGENDARY

        self.add_item(LegendaryChest(), 105 if is_paragon else 5)
        if is_chest:
            return

        self.add_item(ItemCreator(Items.NONE, -1, 0, 0), 20)
        self.add_item(ItemCreator(Items.GOLD, 1, 606, 1200), 20)
        self.add_item(ItemCreator(Items.POWERHOUR, 1), 15)
        self.add_item(ItemCreator(Items.LOCATION, 1), 25)
        self.add_item(ItemCreator(Items.TRASH, 1, 606, 1200, 0.75), 7)

        worst, best = Material.GOLD, Material.VERITE
        self.add_item(ItemCreator(Items.WEAPON, 1, worst, best), 5)
        self.add_item(ItemCreator(Items.BAG, 1, 16, 16), 3)


class MythicalLoot(LootTable):
    """Mythical loot, only spoken in legend."""

    def __init__(self, is_paragon: bool, is_chest: bool = False) -> None:
        super().__init__(5)
        self.rarity = Rarity.MYTHICAL

        self.add_item(MythicalChest(), 105 if is_paragon else 5)
        if is_chest:
            return

        self.add_item(ItemCreator(Items.NONE, -1, 0, 0), 20)
        self.add_item(ItemCreator(Items.GOLD, 1, 810, 1800), 20)
        self.add_item(ItemCreator(Items.POWERHOUR, 1), 15)
        self.add_item(ItemCreator(Items.LOCATION, 1), 25)
        self.add_item(ItemCreator(Items.TRASH, 1, 810, 1800, 0.75), 7)

        worst, best = Material.VERITE, Material.VALORITE
        self.add_item(ItemCreator(Items.WEAPON, 1, worst, best), 5)
        self.add_item(ItemCreator(Items.BAG, 1, 16, 16), 3)
