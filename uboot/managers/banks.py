"""Representation of a bank. Keeps track of several items and manages the
connection between database and memory.
"""
import json
from enum import IntEnum, auto
from typing import Optional

from db.banks import BankDb, BankRaw
from .loot_tables import Item, Items, ItemRaw


def make_raw(user_id: int) -> BankRaw:
    """Creates a raw bank (tuple) fit for storing into a database with
    pre-defined defaults.
    """
    return (user_id, '[]')


class Inventory():
    """Represents an inventory that can store items."""

    class Type(IntEnum):
        BASE = auto()
        BANK = auto()
        RESOURCES = auto()
        BAG = auto()

    def __init__(self, inventory_type: Type = Type.BASE,
                 name: str = "Inventory",
                 capacity: int = 4,
                 items: list[Item] = [],
                 parent: Optional['Inventory'] = None) -> None:
        self.type = inventory_type
        self._capacity = capacity
        self.items = [item for item in items if item.isreal]
        self.name = name
        self.parent = parent

    @property
    def value(self) -> int:
        """Gets the total value of the bank."""
        total_value: int = 0
        for item in self.items:
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
        for item in self.items:
            if item.type == Items.BAG:
                c_capacity += item.uses
        return c_capacity

    def raw_items(self) -> list[ItemRaw]:
        """Converts items into a raw value for database storage."""
        return [item._raw for item in self.items if item.isreal]

    def get_item(self, item_type: Items, name: str,
                 value: int) -> Optional[Item]:
        """Attempts to get an item based on some values."""
        return next((i for i in self.items if i.type == item_type and
                     i.value == value and i.name == name), None)

    def use_stackable(self, item: Item) -> bool:
        """Uses a consumable item."""
        if not item.isstackable:
            return False

        owned = next((i for i in self.items if i.type == item.type), None)
        if not owned:
            return False

        owned.remove_use(1)
        return True

    def add_item(self, item: Item, uses_override: int = -1,
                 max_override=False) -> None:
        """Add an item to the users bank, ignoring if bank is full."""
        if not item.isreal:
            return

        # If uses are not added.
        if not item.isstackable:
            if not max_override and len(self.items) >= self.max_capacity:
                return
            self.items.append(item)
            return

        # Attempt to add stacks or uses.
        owned: Optional[Item] = None
        for i in self.items:
            if i.type == item.type and int(i.material) == int(item.material):
                owned = i
                break

        if not owned:
            if len(self.items) < self.max_capacity or max_override:
                if uses_override > 0:
                    item.uses = uses_override
                self.items.append(item)
            return

        # Add the uses.
        if uses_override < 0:
            uses_override = item.uses
        owned.add_use(uses_override)

    def remove_item(self, item_type: Items, name: str, value: int) -> bool:
        """Remove an item from the users bank."""
        new_items: list[Item] = []
        for i in self.items:
            if i.type == item_type and i.value == value and i.name == name:
                continue
            new_items.append(i)

        old_count = len(self.items)
        self.items = new_items
        return old_count != new_items


class ResourceBag(Inventory):
    """Representation of a bag containing resources."""

    def __init__(self, items: list[Item], parent: Inventory) -> None:
        items = [item for item in items if item.isresource]
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
        resources = [item for item in items if item.isresource]
        bankable = [item for item in items if not item.isresource]
        super().__init__(inventory_type=Inventory.Type.BANK,
                         name="Bank Box",
                         capacity=4,
                         items=bankable)

        self.user_id = raw[0]
        self.bags: list[Inventory] = [ResourceBag(resources, self)]

    @property
    def _raw(self) -> BankRaw:
        """Converts the Bank back into a BankRaw."""
        items = [*self.raw_items(), *self.resources.raw_items()]
        return (self.user_id, f"'{json.dumps(items)}'")

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
        if item.isresource:
            self.resources.add_item(item, uses_override, max_override)
            return

        super().add_item(item, uses_override, max_override)

    def remove_item(self, item_type: Items, name: str, value: int) -> bool:
        """Removes an item from bank or resource bag."""
        if super().remove_item(item_type, name, value):
            return True

        return self.resources.remove_item(item_type, name, value)

    def save(self) -> None:
        """Stores the bank into the database, saving or updating as necesarry."""
        if Manager._db:
            Manager._db.update(self._raw)


class Manager():
    """Manages the Bank database in memory and in storage."""
    _db: Optional[BankDb] = None
    _banks: dict[int, Bank] = {}

    @staticmethod
    def init(dbname: str) -> None:
        """Initializes the Bank Manager, connecting and loading from
        database.
        """
        Manager._db = BankDb(dbname)
        raw_banks = Manager._db.find_all()
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
    def getall() -> list[Bank]:
        """Gets all of the banks being managed."""
        return list(Manager._banks.values())
