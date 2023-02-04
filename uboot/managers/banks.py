"""Representation of a bank. Keeps track of several items and manages the
connection between database and memory.
"""
import json
from enum import IntEnum, auto
from typing import Optional

from db.banks import BankDb, BankRaw
from .loot_tables import Item, Items, ItemRaw, Material


def make_raw(user_id: int) -> BankRaw:
    """Creates a raw bank (tuple) fit for storing into a database with
    pre-defined defaults.
    """
    return user_id, '[]'


class Inventory:
    """Represents an inventory that can store items."""

    class Type(IntEnum):
        BASE = auto()
        BANK = auto()
        RESOURCES = auto()
        BAG = auto()

    def __init__(self, inventory_type: Type = Type.BASE,
                 name: str = "Inventory",
                 capacity: int = 4,
                 items: list[Item] = None,
                 parent: Optional['Inventory'] = None) -> None:
        self.type = inventory_type
        self._capacity = capacity
        self.name = name
        self.parent = parent
        self.items: dict[str, Item] = {}

        items = [] if items is None else items
        for item in items:
            if item.is_real:
                self.items[item.id] = item

    @property
    def value(self) -> int:
        """Gets the total value of the bank."""
        total_value: int = 0
        for item in self.items.values():
            total_value += item.value
        return total_value

    @property
    def base_capacity(self) -> int:
        """Gets the unmodified capacity of a container."""
        return self._capacity

    @property
    def max_capacity(self) -> int:
        """Gets the custom capacity of the users bank."""
        c_capacity: int = self.base_capacity
        for item in self.items.values():
            if item.type == Items.BAG:
                c_capacity += item.uses
        return c_capacity

    def raw_items(self) -> list[ItemRaw]:
        """Converts items into a raw value for database storage."""
        return [item.raw for item in self.items.values() if item.is_real]

    def get_item(self, item_id: str) -> Optional[Item]:
        """Attempts to get an item based on some values."""
        return self.items[item_id]

    def get_item_by_type(self, item_type: Items,
                         item_material: Optional[Material],
                         ) -> Optional[Item]:
        """Get an item based on the type and optional material."""
        for item in self.items.values():
            if item_material and int(item_material) != int(item.material):
                continue

            if item.type == item_type:
                return item

    def use_stackable(self, item: Item) -> bool:
        """Uses a consumable item."""
        if not item.is_stackable:
            return False

        owned = self.get_item_by_type(item.type, item.material)
        if not owned:
            return False

        owned.remove_use(1)
        return True

    def add_item(self, item: Item, uses_override: int = -1,
                 max_override=False) -> None:
        """Add an item to the users bank, ignoring if bank is full."""
        if not item.is_real:
            return

        # If uses are not added.
        if not item.is_stackable:
            if not max_override and len(self.items) >= self.max_capacity:
                return
            self.items[item.id] = item
            return

        # Attempt to add stacks or uses.
        owned = self.get_item_by_type(item.type, item.material)
        if not owned:
            if len(self.items) < self.max_capacity or max_override:
                if uses_override > 0:
                    item.uses = uses_override
                self.items[item.id] = item
            return

        # Add the uses.
        if uses_override < 0:
            uses_override = item.uses
        owned.add_use(uses_override)

    def remove_item(self, item_id: str) -> bool:
        """Remove an item from the users bank."""
        old_count = len(self.items)
        del self.items[item_id]
        return old_count != len(self.items)


class ResourceBag(Inventory):
    """Representation of a bag containing resources."""

    def __init__(self, items: list[Item], parent: Inventory) -> None:
        items = [item for item in items if item.is_resource]
        super().__init__(inventory_type=Inventory.Type.RESOURCES,
                         name="Resource Pouch",
                         capacity=16,
                         items=items,
                         parent=parent)


class Bank(Inventory):
    """Representation of a bank. Initialized with BankRaw."""

    def __init__(self, raw: BankRaw) -> None:
        # Load the items.
        raw_items = json.loads(raw[1].replace("'", ''))

        # Convert the items.
        items = [Item.from_raw(item) for item in raw_items]
        resources = [item for item in items if item.is_resource]
        bankable = [item for item in items if not item.is_resource]
        super().__init__(inventory_type=Inventory.Type.BANK,
                         name="Bank Box",
                         capacity=4,
                         items=bankable)

        self.user_id = raw[0]
        self.bags: list[Inventory] = [ResourceBag(resources, self)]

    @property
    def raw(self) -> BankRaw:
        """Converts the Bank back into a BankRaw."""
        items = [*self.raw_items(), *self.resources.raw_items()]
        return self.user_id, f"'{json.dumps(items)}'"

    @property
    def resources(self) -> ResourceBag:
        """Gets the resource bag for the users bank"""
        resource_bag: Optional[ResourceBag] = None
        for b in self.bags:
            if b.type == Inventory.Type.RESOURCES and isinstance(
                    b, ResourceBag):
                resource_bag = b
                break

        # Create the resource bag if it is missing somehow.
        if not resource_bag:
            resource_bag = ResourceBag([], self)
            self.bags.append(resource_bag)

        return resource_bag

    def add_item(self, item: Item, uses_override: int = -1,
                 max_override=False) -> None:
        """Add an item to the users bank or resource bag."""
        if item.is_resource:
            self.resources.add_item(item, uses_override, max_override)
            return

        super().add_item(item, uses_override, max_override)

    def remove_item(self, item_id: str) -> bool:
        """Removes an item from bank or resource bag."""
        if super().remove_item(item_id):
            return True

        return self.resources.remove_item(item_id)

    def save(self) -> None:
        """Stores the bank into the database, saving or updating as necessary."""
        if Manager.db:
            Manager.db.update(self.raw)


class Manager:
    """Manages the Bank database in memory and in storage."""
    db: Optional[BankDb] = None
    _banks: dict[int, Bank] = {}

    @staticmethod
    def init(dbname: str) -> None:
        """Initializes the Bank Manager, connecting and loading from
        database.
        """
        Manager.db = BankDb(dbname)
        raw_banks = Manager.db.find_all()
        for raw in raw_banks:
            Manager.add(Bank(raw))

    @staticmethod
    def add(bank: Bank) -> Bank:
        """Adds a bank to memory, does not save it to database."""
        Manager._banks[bank.user_id] = bank
        return bank

    @staticmethod
    def get(user_id: int) -> Bank:
        """Get a bank based on its user id. If it does not exist,
        it will be initialized with defaults.
        """
        bank = Manager._banks.get(user_id)
        if not bank:
            # Create and add it to the manager.
            bank = Bank(make_raw(user_id))
            Manager.add(bank)
        return bank

    @staticmethod
    def get_all() -> list[Bank]:
        """Gets all the banks being managed."""
        return list(Manager._banks.values())
