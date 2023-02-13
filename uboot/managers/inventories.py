"""Representation of a bank. Keeps track of several items and manages the
connection between database and memory.
"""
import json
import uuid
from enum import IntEnum, auto
from typing import Optional, Union

from db.inventories import InventoryDb, InventoryRaw
from .items import Item, Items, Material, Reagent, Manager as ItemManager


def make_raw(user_id: int, inventory_id: str) -> InventoryRaw:
    """Creates a raw inventory (tuple) fit for storing into a database with
    pre-defined defaults.
    """
    return user_id, inventory_id, int(Inventory.Type.BASE), 4, \
        "Bag", "", "[]"


class Inventory:
    """Represents an inventory that can store items."""
    BAG_CAP: int = 2

    class Type(IntEnum):
        """Various types of inventories that exist."""
        BASE = auto()
        BACKPACK = auto()
        BANK = auto()
        RESOURCES = auto()
        BAG = auto()

    def __init__(self,
                 user_id: int,
                 inventory_id: str = str(uuid.uuid4()),
                 inventory_type: Type = Type.BASE,
                 capacity: int = 4,
                 name: str = "Inventory",
                 item_ids: Optional[list[str]] = None,
                 parent_id: str = "0") -> None:
        self.user_id = user_id
        self.id = inventory_id.replace("'", "")
        self.type = inventory_type
        self._capacity = capacity
        self.base_name = name.replace("'", "")
        self.parent_id = parent_id.replace("'", "")
        self.item_ids: list[str] = item_ids if item_ids else []
        self.items: dict[str, Item] = {}

    @staticmethod
    def from_raw(raw: InventoryRaw) -> 'Inventory':
        """Converts an inventory from a raw value to a real value."""
        item_ids: list[str] = json.loads(raw[6].replace("'", ''))
        return Inventory(user_id=int(raw[0]),
                         inventory_id=raw[1],
                         inventory_type=Inventory.Type(int(raw[2])),
                         capacity=int(raw[3]),
                         name=raw[4],
                         parent_id=raw[5],
                         item_ids=item_ids,
                         )

    @property
    def is_heavy(self) -> bool:
        """Checks if there are too many items in a bag."""
        return len(self.items) >= self.max_capacity

    @property
    def is_bag_capped(self) -> bool:
        """Checks if there are too many bags."""
        cap = Inventory.BAG_CAP
        if self.type == Inventory.Type.BACKPACK:
            cap += 2
        return len(self.get_bags()) >= cap

    @property
    def value(self) -> int:
        """Gets the total value of the bank."""
        total_value: int = 0
        for item in self.items.values():
            total_value += item.value
        return total_value

    @property
    def name(self) -> str:
        """Gets the name for the inventory with slot count."""
        return f"{self.base_name} [slots: {self.max_capacity}]"

    @property
    def base_capacity(self) -> int:
        """Gets the unmodified capacity of a container."""
        return self._capacity

    @property
    def max_capacity(self) -> int:
        """Gets the custom capacity of the users bank."""
        return self.base_capacity

    @property
    def raw(self) -> InventoryRaw:
        """Converts an inventory back into a InventoryRaw."""
        return self.user_id, f"'{self.id}'", int(self.type), \
            self._capacity, f"'{self.base_name}'", f"'{self.parent_id}'", \
            f"'{json.dumps(self.item_ids)}'"

    def get_bags(self) -> list['Inventory']:
        """Obtain all bags that belong in the current one."""
        bags: list['Inventory'] = []
        for bag in Manager.inventories.values():
            if bag.parent_id == self.id:
                bags.append(bag)
        return bags

    def get_item(self, item_id: str) -> Optional[Item]:
        """Attempts to get an item based on some values."""
        return self.items[item_id]

    def get_item_by_type(self, item_type: Items,
                         item_material: Optional[Union[Material, Reagent]],
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
        owned.save()
        return True

    def add_item(self, item: Item, uses_override: int = -1,
                 max_override: bool = False) -> bool:
        """Add an item to the users bank, ignoring if bank is full."""
        if not item.is_real:
            return False

        # If uses are not added.
        if not item.is_stackable:
            if not max_override and len(self.items) >= self.max_capacity:
                return False
            self.items[item.id] = item
            self.item_ids.append(item.id)
            ItemManager.add(item)
            item.save()
            return True

        # Attempt to add stacks or uses.
        owned = self.get_item_by_type(item.type, item.material)
        if not owned:
            if len(self.items) < self.max_capacity or max_override:
                if uses_override > 0:
                    item.uses = uses_override
                self.items[item.id] = item
                self.item_ids.append(item.id)
                ItemManager.add(item)
                item.save()
                return True
            return False

        # Add the uses.
        if uses_override < 0:
            uses_override = item.uses
        owned.add_use(uses_override)
        owned.save()
        return True

    def remove_item(self, item_id: str, delete: bool = True) -> bool:
        """Remove an item from the users bank."""
        old_count = len(self.item_ids)
        self.item_ids = [item for item in self.item_ids if item != item_id]
        del self.items[item_id]
        if old_count != len(self.item_ids):
            if delete:
                ItemManager.remove(item_id)
            return True
        return False

    def save(self) -> None:
        """Stores the inventory into the database, saving or updating
        as necessary.
        """
        if Manager.db:
            Manager.db.update(self.raw)


class ResourceBag(Inventory):
    """Representation of a bag containing resources."""

    def __init__(self, user_id: int,
                 inventory_id: str,
                 item_ids: list[str]) -> None:
        super().__init__(
            user_id=user_id,
            inventory_id=inventory_id,
            inventory_type=Inventory.Type.RESOURCES,
            capacity=16,
            name="Resource Pouch",
            parent_id=str(user_id),
            item_ids=item_ids)

    @staticmethod
    def from_raw(raw: InventoryRaw) -> 'ResourceBag':
        """Converts an inventory from a raw value to a real value."""
        item_ids: list[str] = json.loads(raw[6].replace("'", ''))
        return ResourceBag(user_id=int(raw[0]),
                           inventory_id=raw[1],
                           item_ids=item_ids,
                           )


class Backpack(Inventory):
    """Representation of a backpack. Initialized with InventoryRaw."""

    def __init__(self, user_id: int,
                 item_ids: list[str]) -> None:
        super().__init__(
            user_id=user_id,
            inventory_id=str(user_id),
            inventory_type=Inventory.Type.BACKPACK,
            capacity=8,
            name="Backpack",
            parent_id="0",
            item_ids=item_ids)

    @staticmethod
    def from_raw(raw: InventoryRaw) -> 'Backpack':
        """Converts an inventory from a raw value to a real value."""
        item_ids: list[str] = json.loads(raw[6].replace("'", ''))
        return Backpack(user_id=int(raw[0]), item_ids=item_ids)

    @property
    def resources(self) -> ResourceBag:
        """Gets the resource bag for the users bank"""
        return Manager.get_resource(self.user_id)

    def add_item(self, item: Item, uses_override: int = -1,
                 max_override=False) -> None:
        """Add an item to the users bank or resource bag."""
        if item.is_resource:
            added = self.resources.add_item(item,
                                            uses_override,
                                            max_override)
            if added:
                self.resources.save()
            return

        super().add_item(item, uses_override, max_override)

    def remove_item(self, item_id: str, delete: bool = True) -> bool:
        """Removes an item from bank or resource bag."""
        if super().remove_item(item_id, delete):
            return True

        if self.resources.remove_item(item_id, delete):
            self.resources.save()
            return True
        return False


class Bank(Inventory):
    """Representation of a bank. Initialized with InventoryRaw."""

    def __init__(self, user_id: int,
                 inventory_id: str,
                 item_ids: list[str]) -> None:
        super().__init__(
            user_id=user_id,
            inventory_id=inventory_id,
            inventory_type=Inventory.Type.BANK,
            capacity=12,
            name="Bank Box",
            parent_id=str(user_id),
            item_ids=item_ids)

    @staticmethod
    def from_raw(raw: InventoryRaw) -> 'Bank':
        """Converts an inventory from a raw value to a real value."""
        item_ids: list[str] = json.loads(raw[6].replace("'", ''))
        return Bank(user_id=int(raw[0]),
                    inventory_id=raw[1],
                    item_ids=item_ids,
                    )


class Manager:
    """Manages the Bank database in memory and in storage."""
    db: Optional[InventoryDb] = None
    inventories: dict[str, Inventory] = {}  # Inventory ID => Inventory
    _backpacks: dict[int, Backpack] = {}  # User ID => Backpack
    _banks: dict[int, Bank] = {}  # User ID => Bank
    _resources: dict[int, ResourceBag] = {}  # User ID => ResourceBag

    @staticmethod
    def init(dbname: str) -> None:
        """Initializes the Inventory Manager, connecting and loading from
        database.
        """
        Manager.db = InventoryDb(dbname)
        raw_inventories = Manager.db.find_all()
        for raw in raw_inventories:
            inventory_type = Inventory.Type(int(raw[2]))
            if inventory_type == Inventory.Type.BACKPACK:
                inventory = Backpack.from_raw(raw)
            elif inventory_type == Inventory.Type.BANK:
                inventory = Bank.from_raw(raw)
            elif inventory_type == Inventory.Type.RESOURCES:
                inventory = ResourceBag.from_raw(raw)
            else:
                inventory = Inventory.from_raw(raw)
            Manager.add(inventory)

        # Make sure a resource bag exists for each bank.
        for bank in Manager._banks.values():
            if not Manager._resources.get(bank.user_id, None):
                Manager._create_resource(bank.user_id)

    @staticmethod
    def add(inventory: Union[Inventory, ResourceBag, Bank]):
        """Adds an inventory to memory, does not save it to database."""
        # Get all the items from the database and update.
        new_ids: list[str] = []
        for item_id in inventory.item_ids:
            item = ItemManager.get(item_id)
            if item:
                new_ids.append(item_id)
                inventory.items[item_id] = item
        if len(new_ids) != len(inventory.item_ids):
            inventory.item_ids = new_ids
            inventory.save()

        Manager.inventories[inventory.id] = inventory
        if isinstance(inventory, Backpack):
            Manager._backpacks[inventory.user_id] = inventory
        elif isinstance(inventory, Bank):
            Manager._banks[inventory.user_id] = inventory
        elif isinstance(inventory, ResourceBag):
            Manager._resources[inventory.user_id] = inventory
        return inventory

    @staticmethod
    def get(inventory_id: str) -> Optional[Inventory]:
        """Get an inventory based on its id."""
        return Manager.inventories.get(inventory_id, None)

    @staticmethod
    def get_backpack(user_id: int) -> Backpack:
        """Get a backpack based on its user id. If it does not exist,
        it will be initialized with defaults.
        """
        backpack = Manager._backpacks.get(user_id, None)
        if not backpack:
            backpack = Manager._create_backpack(user_id)

        if not Manager._resources.get(user_id, None):
            Manager._create_resource(user_id)

        if not Manager._banks.get(user_id, None):
            Manager._create_bank(user_id)

        return backpack

    @staticmethod
    def _create_backpack(user_id: int) -> Backpack:
        """Creates a backpack for the user id."""
        backpack = Manager._backpacks.get(user_id, None)
        if backpack:
            return backpack
        backpack = Backpack(user_id, [])
        Manager._backpacks[user_id] = backpack
        Manager.inventories[backpack.id] = backpack
        backpack.save()
        return backpack

    @staticmethod
    def get_bank(user_id: int) -> Bank:
        """Get a bank box based on its user id. If it does not exist,
        it will be initialized with defaults.
        """
        bank = Manager._banks.get(user_id, None)
        if not bank:
            bank = Manager._create_bank(user_id)

        if not Manager._resources.get(user_id, None):
            Manager._create_resource(user_id)

        return bank

    @staticmethod
    def _create_bank(user_id: int) -> Bank:
        """Creates a bank for the user id."""
        bank = Manager._banks.get(user_id, None)
        if bank:
            return bank

        bank = Bank(user_id=user_id,
                    inventory_id=str(uuid.uuid4()),
                    item_ids=[])
        Manager._banks[user_id] = bank
        Manager.inventories[bank.id] = bank
        bank.save()
        return bank

    @staticmethod
    def get_resource(user_id: int) -> ResourceBag:
        """Get a resource bag based on its user id. If it does not exist,
        it will be initialized with defaults.
        """
        resource = Manager._resources.get(user_id, None)
        if not resource:
            # Create and add it to the manager. Creates backpack if missing.
            backpack = Manager.get_backpack(user_id)
            resource = Manager._create_resource(backpack.user_id)
        return resource

    @staticmethod
    def _create_resource(user_id: int) -> ResourceBag:
        """Creates a resource bag for the user id."""
        resource = Manager._resources.get(user_id, None)
        if resource:
            return resource

        resource = ResourceBag(user_id=user_id,
                               inventory_id=str(uuid.uuid4()),
                               item_ids=[])
        Manager._resources[user_id] = resource
        Manager.inventories[resource.id] = resource
        resource.save()
        return resource

    @staticmethod
    def get_bags(user_id: int) -> list[Inventory]:
        """Gets all the inventories belonging to a user."""
        inventories: list[Inventory] = []
        for inventory in Manager.inventories.values():
            if inventory.user_id == user_id:
                inventories.append(inventory)

        return inventories
