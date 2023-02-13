import uuid
from enum import IntEnum, auto
from typing import Optional, Union

from db.items import ItemDb, ItemRaw


class Items(IntEnum):
    """Represents all the item types that can exist."""
    NONE = auto()
    GOLD = auto()
    POWERHOUR = auto()
    LOCATION = auto()
    WEAPON = auto()
    TRASH = auto()
    REAGENT = auto()
    ORE = auto()
    BAG = auto()
    CHEST = auto()


class Rarity(IntEnum):
    """Tiers that a lootpacks and items can be."""
    COMMON = auto()
    UNCOMMON = auto()
    RARE = auto()
    EPIC = auto()
    LEGENDARY = auto()
    MYTHICAL = auto()


class Potion(IntEnum):
    """Types of Potions"""
    POWERHOUR = auto()
    HEAL = auto()
    CURE = auto()
    NIGHTSIGHT = auto()
    RESURRECTION = auto()


class Reagent(IntEnum):
    """Types of reagents."""
    NONE = auto()
    BONE = auto()
    DAEMON_BONE = auto()
    BLACK_PEARL = auto()
    BLOOD_MOSS = auto()
    GARLIC = auto()
    GINSENG = auto()
    MANDRAKE_ROOT = auto()
    NIGHTSHADE = auto()
    SPIDERS_SILK = auto()
    SULFUROUS_ASH = auto()


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


class Item:
    """Represents a unique item."""

    def __init__(self,
                 item_id: str,
                 item_type: Items,
                 name: Optional[str] = None,
                 rarity: Rarity = Rarity.COMMON,
                 material: Union[Material, Reagent] = Material.NONE,
                 value: int = 1,
                 uses: int = 1,
                 uses_max: int = 1):
        self.id = item_id.replace("'", "")
        self.type = item_type
        name = name.replace("'", "") if name else item_type.name.title()
        self._name = name
        self.rarity = rarity
        self.material = material
        self._value = value
        self.uses = uses
        self.uses_max = uses_max

    @property
    def name(self) -> str:
        """Gets the name of the item based on its type."""
        if self.type == Items.REAGENT:
            return Reagent(self.material.value).name.replace("_", ' ')
        elif self.type == Items.BAG:
            return f"{self._name} [slots: {self.uses_max}]"

        rarity: str = ""
        if self.material != Material.NONE:
            rarity = f"{self.material.name.title().replace('_', ' ')} "

        if not self.type.name and not self._name:
            return f'{rarity}Unknown'
        return f'{rarity}{self._name}'

    @property
    def base_value(self) -> int:
        """Base unmodified value of the item."""
        if self.type == Items.POWERHOUR:
            return 20
        if self.type == Items.BAG:
            return 100
        if self.type == Items.WEAPON:
            return 150
        return self._value

    @property
    def value(self) -> int:
        """Gets the value of the item based on its type."""
        base_value = self.base_value

        if self.is_stackable:
            return base_value * self.uses
        if self.type == Items.BAG:
            return base_value * self.uses_max
        if self.type not in (Items.WEAPON,):
            return base_value

        # 0 - 0.5
        material_mod: float = (max(self.material, Material.NONE) - 1) / 5
        uses_mod: float = max(self.uses / self.uses_max, 0)

        return int(base_value * (1 + material_mod) * uses_mod)

    @property
    def raw(self) -> ItemRaw:
        """Gets the raw value of the item, used for database storage."""
        return (f"'{self.id}'", int(self.type), f"'{self._name}'",
                int(self.rarity), int(self.material), self._value, self.uses, self.uses_max)

    @property
    def is_stackable(self) -> bool:
        """Checks if an item can be stacked."""
        return self.type in (Items.POWERHOUR, Items.REAGENT, Items.ORE)

    @property
    def is_resource(self) -> bool:
        """Checks if an item can be stacked."""
        return self.type in (Items.REAGENT, Items.ORE)

    @property
    def is_usable(self) -> bool:
        """Checks if the item can be used."""
        return self.type in (Items.POWERHOUR, Items.WEAPON, Items.BAG)

    @property
    def is_consumable(self) -> bool:
        """Checks if the item can be consumed."""
        return self.type in (Items.POWERHOUR,)

    @property
    def is_real(self) -> bool:
        """Checks if the item is real or just imaginary item."""
        return self.type not in (Items.NONE, Items.GOLD, Items.LOCATION,
                                 Items.CHEST)

    @staticmethod
    def from_raw(raw: ItemRaw) -> 'Item':
        """Creates an item from a raw value."""
        return Item(
            item_id=str(raw[0]),
            item_type=Items(raw[1]),
            name=raw[2],
            rarity=Rarity(raw[3]),
            material=Material(raw[4]),
            value=raw[5],
            uses=raw[6],
            uses_max=raw[7])

    def add_use(self, value: int) -> None:
        """Adds a use to an object."""
        if value <= 0:
            return
        self.uses = min(self.uses + value, self.uses_max)

    def remove_use(self, value: int) -> None:
        """Removes uses from an object."""
        if value <= 0:
            return
        self.uses = max(self.uses - value, 0)

    def save(self) -> None:
        """Stores the item into the database, saving or updating
        as necessary.
        """
        if Manager.db:
            Manager.db.update(self.raw)

    def remove(self) -> None:
        """Removes the item from the database."""
        if Manager.db:
            Manager.db.delete_one(self.raw)


class Chest(Item):
    """Represents a chest with multiple items."""

    def __init__(self, rarity: Rarity, items: list[Item]) -> None:
        super().__init__(str(uuid.uuid4()), Items.CHEST)
        self.rarity = rarity
        self.items = items

    @property
    def name(self) -> str:
        """Gets the name of the item based on its type."""
        return f"A Treasure Chest [{self.rarity.name.capitalize()}]"


class Manager:
    """Manages the item database in memory and in storage."""
    db: Optional[ItemDb] = None
    _items: dict[str, Item] = {}  # Item ID => Item

    @staticmethod
    def init(dbname: str) -> None:
        """Initializes the Item Manager, connecting and loading from
        database.
        """
        Manager.db = ItemDb(dbname)
        raw_items = Manager.db.find_all()
        for raw in raw_items:
            Manager.add(Item.from_raw(raw))

    @staticmethod
    def add(item: Item):
        """Adds an item to memory, does not save it to database."""
        if not item.is_real:
            return
        Manager._items[item.id] = item

    @staticmethod
    def remove(item_id: str):
        """Adds an item to memory, does not save it to database."""
        item = Manager.get(item_id)
        if item:
            item.remove()
            del Manager._items[item.id]

    @staticmethod
    def get(item_id: str) -> Optional[Item]:
        """Get an inventory based on its id."""
        return Manager._items.get(item_id, None)
