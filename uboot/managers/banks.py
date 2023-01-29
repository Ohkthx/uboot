"""Representation of a bank. Keeps track of several items and manages the
connection between database and memory.
"""
from typing import Optional
import json

from db.banks import BankDb, BankRaw
from .loot_tables import Item, Material, Items, ItemRaw


def make_raw(user_id: int) -> BankRaw:
    """Creates a raw bank (tuple) fit for storing into a database with
    pre-defined defaults.
    """
    return (user_id, '[]')


class Bank():
    """Representation of a bank. Initialized with BankRaw."""

    def __init__(self, raw: BankRaw) -> None:
        self.user_id = raw[0]
        self.items: list[Item] = []
        self.capacity = 8

        # Load the items.
        raw_items = json.loads(raw[1].replace("'", ''))
        for item in raw_items:
            self.items.append(Item.from_raw(item))

    @property
    def _raw(self) -> BankRaw:
        """Converts the Bank back into a BankRaw."""
        return (self.user_id, f"'{json.dumps(self.raw_items())}'")

    @property
    def value(self) -> int:
        """Gets the total value of the bank."""
        total_value: int = 0
        for item in self.items:
            total_value += item.value
        return total_value

    def raw_items(self) -> list[ItemRaw]:
        """Converts items into a raw value for database storage."""
        return [item._raw for item in self.items]

    def get_item(self, item_type: Items, name: str,
                 value: int) -> Optional[Item]:
        """Attempts to get an item based on some values."""
        return next((i for i in self.items if i.type == item_type and
                     i.value == value and i.name == name), None)

    def add_item(self, item: Item, uses_override: int = -1,
                 max_override=False) -> None:
        """Add an item to the users bank, ignoring if bank is full."""
        # If uses are not added.
        if not item.isstackable:
            if not max_override and len(self.items) >= self.capacity:
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
            if len(self.items) < self.capacity or max_override:
                if uses_override > 0:
                    item.uses = uses_override
                self.items.append(item)
            return

        # Add the uses.
        if uses_override < 0:
            uses_override = item.uses
        owned.add_use(uses_override)

    def use_consumable(self, item: Item) -> bool:
        """Uses a consumable item."""
        if not item.isconsumable:
            return False

        owned = next((i for i in self.items if i.type == item.type), None)
        if not owned:
            return False

        owned.remove_use(1)
        return True

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
