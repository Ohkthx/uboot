"""User based views."""
from typing import Optional, Union, Type

import discord
from discord import ui

from dclient.helper import get_user, convert_age
from managers import entities
from managers import users
from managers.actions import Action, ItemMove, Manager as ActionManager
from managers.inventories import Inventory, ResourceBag, Manager as InventoryManager
from managers.items import Items, Manager as ItemManager
from managers.locations import (Area, Level, Locations, Floor,
                                Manager as LocationsManager)
from managers.logs import Log


async def extract_users(client: discord.Client,
                        message: discord.Message) -> list[discord.User]:
    """Attempt to get the user from a message with an embed."""
    # Get the embed to extract the user ids.
    if len(message.embeds) == 0:
        return []

    # Extract the user ids from the footer.
    user_ids: list[int] = []
    try:
        if message.embeds[0].footer.text:
            raw_ids = message.embeds[0].footer.text.split(':')
            user_ids = [int(user_id) for user_id in raw_ids]
    except BaseException:
        pass

    # Lookup the users
    extracted_users: list[discord.User] = []
    for user_id in user_ids:
        user = await get_user(client, user_id)
        if user:
            extracted_users.append(user)
    return extracted_users


def show_inventory(inventory: Inventory) -> str:
    """Creates a string containing all the inventories items."""
    # Create a list of items.
    items: list[str] = []
    for n, item in enumerate(inventory.items.values()):
        line_feed = '└' if n + 1 == len(inventory.items) else '├'
        left: str = ""
        value: str = f", {item.value} gp"
        if item.is_resource:
            left = "count: "
            value = ""
        elif item.is_consumable:
            left = "charges: "
        elif item.is_usable and item.type != Items.BAG:
            left = "durability: "

        uses = ""
        if left != "":
            uses = f" [{left}{item.uses} / {item.uses_max}]"
        items.append(f"> {line_feed} **{item.name.title()}**{uses}{value}")

    # If none, print none.
    items_full = '\n'.join(items)
    if len(items) == 0:
        items_full = '> └ **none**'

    return items_full


class LocationDropdown(ui.Select):
    """Allows the user to select a new location."""

    def __init__(self, user: users.User,
                 choice_type: Union[Type[Level], Type[Area]]) -> None:
        self.choice_type = choice_type
        id_expand: str = "area" if choice_type == Area else "level"
        options: list[discord.SelectOption] = []
        choices: dict[str, str] = {}  # Floor/Area ID, Name

        if self.choice_type == Level:
            dungeon_floor = LocationsManager.get(user.c_location, user.c_floor)
            if dungeon_floor:
                for floor in dungeon_floor.parent.get_floors():
                    choices[str(floor.level.value)] = floor.name

        # Populate the choices with ID and NAME of area as a backup.
        if len(choices.items()) == 0:
            for area in user.locations.get_unlocks():
                name = "Unknown"
                if area.name:
                    name = area.name.replace("_", " ").title()
                choices[str(area.value)] = name

        for loc_id, loc_name in choices.items():
            options.append(discord.SelectOption(label=loc_name, value=loc_id))
        super().__init__(options=options,
                         placeholder=f"Recall to a new {id_expand}.",
                         custom_id=f"user_location_{id_expand}_dropdown")

    async def callback(self, interaction: discord.Interaction):
        """Called when the menu is selected."""
        res = interaction.response
        msg = interaction.message
        author = interaction.user
        if not msg:
            await res.send_message("Unknown location, have you discovered it?",
                                   ephemeral=True,
                                   delete_after=30)
            return

        value = int(self.values[0])

        # Changes the user's location, only if it is discovered.
        user = users.Manager.get(author.id)

        if self.choice_type == Level:
            new_loc = user.change_location(user.c_location, Level(value))
        else:
            new_loc = user.change_location(Area(value), Level.ONE)

        view = LocationView(interaction.client)
        view.set_user(author)
        if interaction.message and isinstance(author, discord.User):
            embed = UserStatsView.get_panel(author)
            await interaction.message.edit(embed=embed, view=view)

        if not new_loc:
            await res.send_message("Unknown location, have you discovered it?",
                                   ephemeral=True,
                                   delete_after=30)
            return

        user.save()

        # Create the new view.
        try:
            await msg.edit(embed=LocationView.get_panel(author), view=view)
        except BaseException:
            pass
        await res.send_message(f"Location set to **{new_loc.name}**.",
                               ephemeral=True,
                               delete_after=30)


class BagDropdown(ui.Select):
    """Allows the user to select a specific inventory."""

    def __init__(self, user_id: int, direction: str) -> None:
        options: list[discord.SelectOption] = []
        self.direction = direction

        ignore_bag: str = ""
        action = ActionManager.get(user_id, Action.Types.ITEM_MOVE)
        if action and isinstance(action, ItemMove):
            if self.direction == "source":
                ignore_bag = action.destination_id
            else:
                ignore_bag = action.source_id

        for bag in InventoryManager.get_bags(user_id):
            if isinstance(bag, ResourceBag) or bag.id == ignore_bag:
                continue
            elif self.direction == "destination" and bag.is_heavy:
                continue
            elif self.direction == "source" and len(bag.items) == 0:
                continue

            capacity = f"{len(bag.item_ids)} / {bag.max_capacity}"
            label: str = f"{bag.name.title()}, capacity: {capacity}"
            value: str = bag.id
            options.append(discord.SelectOption(label=label, value=value))
        options.append(discord.SelectOption(label="None", value="none"))
        super().__init__(options=options,
                         placeholder=f"Select {direction} container.",
                         custom_id=f"inventory_move_{direction}_dropdown")

    async def callback(self, interaction: discord.Interaction):
        """Called when the menu is selected."""
        res = interaction.response
        msg = interaction.message
        guild = interaction.guild
        if not msg or not guild:
            return

        extracted_users = await extract_users(interaction.client, msg)
        if len(extracted_users) == 0:
            return await res.send_message("User could not be identified.",
                                          ephemeral=True,
                                          delete_after=20)

        user = extracted_users[0]
        if interaction.user != user:
            return await res.send_message("You cannot use another "
                                          "users bags.",
                                          ephemeral=True,
                                          delete_after=20)

        # None selected.
        if self.values[0] == "none":
            return await res.send_message("Nothing selected.",
                                          ephemeral=True,
                                          delete_after=20)

        inventory = InventoryManager.get(self.values[0])
        if not inventory:
            return await res.send_message("Do you still have that inventory?.",
                                          ephemeral=True,
                                          delete_after=20)

        action = ActionManager.get(user.id, Action.Types.ITEM_MOVE)
        if not action or not isinstance(action, ItemMove):
            action = ItemMove(user.id)
            ActionManager.add(action)
        action.refresh()

        if self.direction == "source":
            action.source_id = self.values[0]
        else:
            action.destination_id = self.values[0]

        try:
            embed = InventoryMoveView.get_panel(user)
            view = InventoryMoveView(interaction.client)
            view.set_user(user, inventory, action)
            await msg.edit(embed=embed, view=view)
        except BaseException:
            pass

        await res.send_message(f"**{self.direction}** container set "
                               f"to **{inventory.name.title()}**",
                               ephemeral=True,
                               delete_after=20)


class ItemDropdown(ui.Select):
    """Allows the user to select a specific item."""

    def __init__(self, user_id: int, inventory_id: str) -> None:
        options: list[discord.SelectOption] = []
        self.inventory_id = inventory_id
        inventory = InventoryManager.get(inventory_id)
        if not inventory:
            inventory = InventoryManager.get_backpack(user_id)

        for item in inventory.items.values():
            label: str = f"{item.name.title()}, value: {item.value} gp"
            value: str = item.id
            options.append(discord.SelectOption(label=label, value=value))
        options.append(discord.SelectOption(label="None", value="none"))
        super().__init__(options=options,
                         placeholder="Select an item.",
                         custom_id="item_dropdown")

    async def callback(self, interaction: discord.Interaction):
        """Called when the menu is selected."""
        res = interaction.response
        msg = interaction.message
        guild = interaction.guild
        if not msg or not guild:
            return

        extracted_users = await extract_users(interaction.client, msg)
        if len(extracted_users) == 0:
            return await res.send_message("User could not be identified.",
                                          ephemeral=True,
                                          delete_after=20)

        user = extracted_users[0]
        if interaction.user != user:
            return await res.send_message("You cannot select another "
                                          "users items.",
                                          ephemeral=True,
                                          delete_after=20)

        # None selected.
        if self.values[0] == "none":
            return await res.send_message("Nothing selected.",
                                          ephemeral=True,
                                          delete_after=20)

        item = ItemManager.get(self.values[0])
        if not item:
            return await res.send_message("Are you sure you still have "
                                          "that item?",
                                          ephemeral=True,
                                          delete_after=20)

        action = ActionManager.get(user.id, Action.Types.ITEM_MOVE)
        if not action or not isinstance(action, ItemMove):
            action = ItemMove(user.id)
            ActionManager.add(action)
        action.refresh()

        action.item_id = self.values[0]

        try:
            embed = InventoryMoveView.get_panel(user)
            await msg.edit(embed=embed)
        except BaseException:
            pass

        await res.send_message(f"**Item** set to **{item.name.title()}**.",
                               ephemeral=True,
                               delete_after=20)


class InventoryShowDropdown(ui.Select):
    """Allows the user to see a specific inventory."""

    def __init__(self, user: users.User, inventory_id: str) -> None:
        options: list[discord.SelectOption] = []
        inventory = InventoryManager.get(inventory_id)
        if not inventory:
            inventory = user.backpack

        for bag in inventory.get_bags():
            label: str = f"{bag.name.title()}, value: {bag.value} gp"
            value: str = bag.id
            options.append(discord.SelectOption(label=label, value=value))
        options.append(discord.SelectOption(label="None", value="none"))
        super().__init__(options=options,
                         placeholder="Open one of your bags.",
                         custom_id="inventory_show_dropdown")

    async def callback(self, interaction: discord.Interaction):
        """Called when the menu is selected."""
        res = interaction.response
        msg = interaction.message
        guild = interaction.guild
        if not msg or not guild:
            return

        extracted_users = await extract_users(interaction.client, msg)
        if len(extracted_users) == 0:
            return await res.send_message("User could not be identified.",
                                          ephemeral=True,
                                          delete_after=20)

        user = extracted_users[0]
        if interaction.user != user:
            return await res.send_message("You cannot view another "
                                          "users items.",
                                          ephemeral=True,
                                          delete_after=20)

        # None selected.
        if self.values[0] == "none":
            return await res.send_message("Nothing selected.",
                                          ephemeral=True,
                                          delete_after=20)

        # Extract the inventory.
        bag = InventoryManager.get(self.values[0])
        if not bag:
            await res.send_message("Could not find bag. "
                                   "Do you still own it?",
                                   ephemeral=True,
                                   delete_after=20)
            return

        # Create the view for the bag.
        view = InventoryView(interaction.client)
        view.set_user(user, bag)

        try:
            embed = InventoryView.get_panel(user, bag)
            await res.send_message(embed=embed, view=view,
                                   ephemeral=True,
                                   delete_after=60)
        except BaseException as exc:
            print(exc)


class InventorySellDropdown(ui.Select):
    """Allows the user to select an item to sell."""

    def __init__(self, inventory: Inventory) -> None:
        options: list[discord.SelectOption] = []
        self.inventory = inventory

        all_label = f"All Items, value: {inventory.value} gp"
        options.append(discord.SelectOption(label=all_label, value="all"))
        for item in inventory.items.values():
            label: str = f"{item.name.title()}, value: {item.value} gp"
            value: str = item.id
            options.append(discord.SelectOption(label=label, value=value))
        options.append(discord.SelectOption(label="None", value="none"))
        super().__init__(options=options,
                         placeholder="Sell Items",
                         custom_id="inventory_sell_dropdown")

    async def callback(self, interaction: discord.Interaction):
        """Called when the menu is selected."""
        res = interaction.response
        msg = interaction.message
        guild = interaction.guild
        if not msg or not guild:
            return

        extracted_users = await extract_users(interaction.client, msg)
        if len(extracted_users) == 0:
            return await res.send_message("User could not be identified.",
                                          ephemeral=True,
                                          delete_after=20)

        user = extracted_users[0]
        if interaction.user != user:
            return await res.send_message("You cannot sell another "
                                          "users items.",
                                          ephemeral=True,
                                          delete_after=20)

        # Extract the item.
        user_l = users.Manager.get(interaction.user.id)
        item_id = self.values[0]

        # None selected.
        if item_id == "none":
            return await res.send_message("Transaction cancelled.",
                                          ephemeral=True,
                                          delete_after=20)

        # Create the new view.
        view = InventoryView(interaction.client)

        # Check if we are selling all items.
        if item_id == "all" and self.inventory.value == 0:
            return await res.send_message("There are no items to sell.",
                                          ephemeral=True,
                                          delete_after=20)
        if item_id == "all":
            total_value = self.inventory.value
            user_l.gold += total_value
            user_l.save()

            removing: list[str] = self.inventory.item_ids
            for item in removing:
                self.inventory.remove_item(item)
            self.inventory.save()

            Log.player(f"{user} sold all items for {total_value} gp!",
                       guild_id=guild.id, user_id=user.id)

            ephemeral: bool = True
            delete_after: Optional[int] = 30
            try:
                embed = InventoryView.get_panel(user, self.inventory)
                view.set_user(user, self.inventory)
                await msg.edit(embed=embed, view=view)
                ephemeral = False
                delete_after = None
            except BaseException:
                pass

            return await res.send_message(f"{user} sold all items "
                                          f"for **{total_value}** gp!",
                                          ephemeral=ephemeral,
                                          delete_after=delete_after)

        # Find the item.
        item = self.inventory.get_item(item_id)
        if not item:
            await res.send_message("Could not find item. Do you still own it?",
                                   ephemeral=True,
                                   delete_after=20)
            return

        quantity: str = ""
        value: int = 0
        if item.is_stackable:
            # Remove a single use of a consumable.
            if item.uses > 0:
                quantity = "one use of " if item.is_consumable else "one "
                value = item.base_value
                self.inventory.use_stackable(item)

            if item.uses == 0:
                self.inventory.remove_item(item.id)
            self.inventory.save()
        else:
            value = item.value
            # Remove the item from the user.
            if self.inventory.remove_item(item.id):
                user_l.gold += value
                user_l.save()
                self.inventory.save()

        Log.player(f"{user} sold {quantity}{item.name.title()} "
                   f"for {value} gp.",
                   guild_id=guild.id, user_id=user.id)

        ephemeral: bool = True
        delete_after: Optional[int] = 30
        try:
            embed = InventoryView.get_panel(user, self.inventory)
            view.set_user(user, self.inventory)
            await msg.edit(embed=embed, view=view)
            ephemeral = False
            delete_after = None
        except BaseException:
            pass

        await res.send_message(f"{user} sold {quantity}"
                               f"**{item.name.title()}** "
                               f"for {value} gp.", ephemeral=ephemeral,
                               delete_after=delete_after)


class InventoryUseDropdown(ui.Select):
    """Allows the user to select an item to use."""

    def __init__(self, inventory: Inventory) -> None:
        options: list[discord.SelectOption] = []
        self.inventory = inventory

        for item in inventory.items.values():
            if not item.is_usable:
                continue
            uses = f"[{item.uses} / {item.uses_max}]"
            if item.type == Items.BAG:
                uses = ""
            label: str = f"{item.name.title()} {uses}"
            value: str = item.id
            options.append(discord.SelectOption(label=label, value=value))
        options.append(discord.SelectOption(label="None", value="none"))
        super().__init__(options=options,
                         placeholder="Use / Equip Item",
                         custom_id="inventory_use_dropdown")

    async def callback(self, interaction: discord.Interaction):
        """Called when the menu is selected."""
        res = interaction.response
        msg = interaction.message
        guild = interaction.guild
        if not msg or not guild:
            return

        extracted_users = await extract_users(interaction.client, msg)
        if len(extracted_users) == 0:
            return await res.send_message("User could not be identified.",
                                          ephemeral=True,
                                          delete_after=20)

        user = extracted_users[0]
        if interaction.user != user:
            return await res.send_message("You cannot use another "
                                          "users items.",
                                          ephemeral=True,
                                          delete_after=20)

        # Extract the item.
        user_l = users.Manager.get(interaction.user.id)
        item_id = self.values[0]

        # None selected.
        if item_id == "none":
            return await res.send_message("No item used.",
                                          ephemeral=True,
                                          delete_after=20)

        # Create the new view.
        view = InventoryView(interaction.client)

        # Find the item.
        item = self.inventory.get_item(item_id)
        if not item:
            return await res.send_message("Could not find item. Do you still "
                                          "own it?",
                                          ephemeral=True,
                                          delete_after=20)

        use_text = "used"

        if item.is_consumable and self.inventory.use_stackable(item):
            granting: str = "granting a powerhour"
            if item.type == Items.POWERHOUR:
                user_l.mark_cooldown(users.Cooldown.POWERHOUR)
            if item.uses == 0:
                self.inventory.remove_item(item.id)
            self.inventory.save()

            Log.player(f"{user} {use_text} {item.name.title()}, {granting}.",
                       guild_id=guild.id, user_id=user.id)

            ephemeral: bool = True
            delete_after: Optional[int] = 30
            try:
                embed = InventoryView.get_panel(user, self.inventory)
                view.set_user(user, self.inventory)
                await msg.edit(embed=embed, view=view)
                ephemeral = False
                delete_after = None
            except BaseException:
                pass
            return await res.send_message(f"{user} {use_text} "
                                          f"**{item.name.title()}**, "
                                          f"{granting}.",
                                          ephemeral=ephemeral,
                                          delete_after=delete_after)

        # Remove the item from the user.
        is_weapon = item.type == Items.WEAPON
        if self.inventory.remove_item(item_id, is_weapon is False):
            # Swap the weapon out.
            if is_weapon:
                use_text = "equipped"
                if user_l.weapon:
                    self.inventory.add_item(user_l.weapon)
                user_l.weapon = item
                user_l.save()
            if item.type == Items.BAG:
                if self.inventory.is_bag_capped:
                    return await res.send_message(f"Cannot fit anymore bags "
                                                  f"within the current bag.",
                                                  ephemeral=True,
                                                  delete_after=20)
                bag = Inventory(user_id=user.id,
                                inventory_type=Inventory.Type.BAG,
                                capacity=item.uses_max,
                                name=item._name,
                                parent_id=self.inventory.id)
                InventoryManager.add(bag)
                bag.save()

            self.inventory.save()

        Log.player(f"{user} {use_text} {item.name.title()}",
                   guild_id=guild.id, user_id=user.id)

        ephemeral: bool = True
        delete_after: Optional[int] = 30
        try:
            embed = InventoryView.get_panel(user, self.inventory)
            view.set_user(user, self.inventory)
            await msg.edit(embed=embed, view=view)
            ephemeral = False
            delete_after = None
        except BaseException:
            pass
        await res.send_message(f"{user} {use_text} **{item.name.title()}**.",
                               ephemeral=ephemeral, delete_after=delete_after)


class TradeDropdown(ui.Select):
    """Allows the user to select an item to trade."""

    def __init__(self, inventory: Inventory) -> None:
        options: list[discord.SelectOption] = []
        self.inventory = inventory

        for item in inventory.items.values():
            item_value: int = item.value
            if item.is_consumable:
                item_value = item.base_value
            label: str = f"{item.name.title()}, value: {item_value} gp"
            value: str = item.id
            options.append(discord.SelectOption(label=label, value=value))
        options.append(discord.SelectOption(label="None", value="none"))
        super().__init__(options=options,
                         placeholder="Give / Trade Item",
                         custom_id="inventory_trade_dropdown")

    async def callback(self, interaction: discord.Interaction):
        """Called when the menu is selected."""
        res = interaction.response
        msg = interaction.message
        guild = interaction.guild
        if not msg or not guild:
            return

        extracted_users = await extract_users(interaction.client, msg)
        if len(extracted_users) <= 1:
            await res.send_message("Users could not be identified.",
                                   ephemeral=True,
                                   delete_after=20)
            return

        if interaction.user != extracted_users[0]:
            await res.send_message("You cannot use another users items.",
                                   ephemeral=True,
                                   delete_after=20)
            return

        # Extract the item.
        user_l = users.Manager.get(interaction.user.id)
        item_id = self.values[0]

        # None selected.
        if item_id == "none":
            await res.send_message("No item given.",
                                   ephemeral=True,
                                   delete_after=20)
            return

        # Find the item.
        item = self.inventory.get_item(item_id)
        if not item:
            await res.send_message("Could not find item. Do you still own it?",
                                   ephemeral=True,
                                   delete_after=20)
            return

        user = extracted_users[0]
        to_user = users.Manager.get(extracted_users[1].id)

        quantity: str = ""
        if item.is_consumable:
            # Remove a single use of a consumable.
            if item.uses > 0:
                quantity = "one use of "
                self.inventory.use_stackable(item)
                to_user.backpack.add_item(item,
                                          uses_override=1,
                                          max_override=True)

            if item.uses == 0:
                self.inventory.remove_item(item.id)
            self.inventory.save()
            to_user.backpack.save()
        else:
            # Remove the item from the user.
            if self.inventory.remove_item(item.id):
                self.inventory.save()
                to_user.backpack.add_item(item, max_override=True)
                to_user.backpack.save()

        value = item.base_value if item.is_consumable else item.value

        log_text = f"{user} gave {quantity}**{item.name.title()}** " \
                   f"(value: {value} gp) to {extracted_users[1]}."
        Log.player(log_text.replace('*', ''),
                   guild_id=guild.id, user_id=user.id)
        Log.player(f"{extracted_users[1]} received {quantity}"
                   f"{item.name.title()} (value: {value} gp) from {user}.",
                   guild_id=guild.id, user_id=extracted_users[1].id)

        view = TradeView(interaction.client)
        view.set_user(user)

        embed = InventoryView.get_panel(user, self.inventory)
        embed.set_footer(text=f"{user_l.id}:{to_user.id}")
        await msg.edit(embed=embed, view=view)
        await res.send_message(log_text)


class EntityDropdown(ui.Select):
    """Allows the user to select a specific entities."""

    def __init__(self, dungeon_floor: Floor) -> None:
        options: list[discord.SelectOption] = []

        for name in entities.Manager.floor_spawns(dungeon_floor):
            label: str = f"{name.title()}"
            value: str = name
            options.append(discord.SelectOption(label=label, value=value))
        options.append(discord.SelectOption(label="None", value="none"))
        super().__init__(options=options,
                         placeholder="Select an entity.",
                         custom_id="entity_dropdown")

    async def callback(self, interaction: discord.Interaction):
        """Called when the menu is selected."""
        res = interaction.response
        msg = interaction.message
        guild = interaction.guild
        if not msg or not guild:
            return

        extracted_users = await extract_users(interaction.client, msg)
        if len(extracted_users) == 0:
            return await res.send_message("User could not be identified.",
                                          ephemeral=True,
                                          delete_after=20)

        user = extracted_users[0]
        if interaction.user != user:
            return await res.send_message("You are not performing the "
                                          "inspection.",
                                          ephemeral=True,
                                          delete_after=20)

        # None selected.
        if self.values[0] == "none":
            return await res.send_message("Nothing selected.",
                                          ephemeral=True,
                                          delete_after=20)

        locations = entities.Manager.entity_locations(self.values[0])

        # Build list of locations
        loc_list: list[str] = []
        for n, loc in enumerate(locations):
            line_feed = '└' if n + 1 == len(locations) else '├'
            loc_list.append(f"> {line_feed} {loc.name}")
        loc_text = '\n'.join(loc_list)

        embed = discord.Embed(title=self.values[0].title())
        embed.colour = discord.Colour.from_str("#00ff08")
        embed.description = f"All known locations for this entity:\n" \
                            f"{loc_text}"

        await res.send_message(embed=embed, ephemeral=True, delete_after=60)


class ConfirmButton(ui.Button):
    def __init__(self, action: Action.Types) -> None:
        self.action = action
        super().__init__(label="Confirm",
                         style=discord.ButtonStyle.green,
                         custom_id="confirm_button")

    async def callback(self, interaction: discord.Interaction) -> None:
        """Called when the confirmation button is clicked."""
        res = interaction.response
        msg = interaction.message
        guild = interaction.guild
        if not msg or not guild:
            return

        extracted_users = await extract_users(interaction.client, msg)
        if len(extracted_users) == 0:
            return await res.send_message("User could not be identified.",
                                          ephemeral=True,
                                          delete_after=20)

        user = extracted_users[0]
        if interaction.user != user:
            return await res.send_message("You did not invoke this action.",
                                          ephemeral=True,
                                          delete_after=20)

        action_type: Type[Union[Action, ItemMove]] = Action
        if self.action == Action.Types.ITEM_MOVE:
            action_type = ItemMove

        action = ActionManager.get(user.id, self.action)
        if not action or not isinstance(action, action_type):
            return await res.send_message("Additional options need to "
                                          "be selected.",
                                          ephemeral=True,
                                          delete_after=20)

        text: str = "Unknown action taken."
        if isinstance(action, ItemMove):
            # Move an item to a new inventory.
            from_inventory = InventoryManager.get(action.source_id)
            to_inventory = InventoryManager.get(action.destination_id)
            if not from_inventory or not to_inventory:
                return await res.send_message("Are you sure you have those "
                                              "bags still?",
                                              ephemeral=True,
                                              delete_after=20)

            item = ItemManager.get(action.item_id)
            if not item:
                return await res.send_message("Are you sure you have that "
                                              "item still?",
                                              ephemeral=True,
                                              delete_after=20)

            if len(to_inventory.items) >= to_inventory.max_capacity:
                return await res.send_message("The bag being moved to is "
                                              "at its capacity.",
                                              ephemeral=True,
                                              delete_after=20)

            if not from_inventory.items.get(item.id, None):
                return await res.send_message("That bag no longer contains "
                                              "that item.",
                                              ephemeral=True,
                                              delete_after=20)

            from_inventory.remove_item(item.id, False)
            to_inventory.add_item(item)
            from_inventory.save()
            to_inventory.save()
            text = f"**{item.name.title()}** moved to **{to_inventory.name}**."
        await res.send_message(text, ephemeral=True, delete_after=20)


class CancelButton(ui.Button):
    def __init__(self, action: Action.Types) -> None:
        self.action = action
        super().__init__(label="Cancel",
                         style=discord.ButtonStyle.red,
                         custom_id="cancel_button")

    async def callback(self, interaction: discord.Interaction) -> None:
        """Called when the confirmation button is clicked."""
        res = interaction.response
        msg = interaction.message
        guild = interaction.guild
        if not msg or not guild:
            return

        extracted_users = await extract_users(interaction.client, msg)
        if len(extracted_users) == 0:
            return await res.send_message("User could not be identified.",
                                          ephemeral=True,
                                          delete_after=20)

        user = extracted_users[0]
        if interaction.user != user:
            return await res.send_message("You did not invoke this action.",
                                          ephemeral=True,
                                          delete_after=20)

        # Cancel the action.
        ActionManager.remove(user.id, self.action)
        try:
            await msg.delete()
        except BaseException:
            pass

        await res.send_message("Action cancelled.",
                               ephemeral=True,
                               delete_after=20)


class InspectView(ui.View):
    """Inspect View checks the surrounding area for information."""

    def __init__(self, bot: discord.Client) -> None:
        self.bot = bot
        self.user: Optional[Union[discord.User, discord.Member]] = None
        super().__init__(timeout=None)

    def set_user(self, user: Union[discord.User, discord.Member]) -> None:
        """Sets the user so their locations can be used in the dropdown."""
        self.user = user
        user_l = users.Manager.get(user.id)
        dungeon_floor = LocationsManager.get(user_l.c_location, user_l.c_floor)
        if not dungeon_floor:
            dungeon_floor = LocationsManager.starting_area()

        self.add_item(EntityDropdown(dungeon_floor))

    @staticmethod
    def get_panel(user: Union[discord.User, discord.Member]) -> discord.Embed:
        """Gets the user stats for the user provided."""
        # Get the local user.
        user_l = users.Manager.get(user.id)
        dungeon_floor = LocationsManager.get(user_l.c_location, user_l.c_floor)
        if not dungeon_floor:
            dungeon_floor = LocationsManager.starting_area()
        dungeon = dungeon_floor.parent

        # Build list of connections
        conn_list: list[str] = []
        connections = Locations.connections(dungeon.area)
        for n, loc in enumerate(connections):
            line_feed = '└' if n + 1 == len(connections) else '├'
            name = "Unknown"
            if loc.name:
                name = loc.name.replace("_", " ").title()
            conn_list.append(f"> {line_feed} {name}")
        conn_text = '\n'.join(conn_list)

        # Build list of spawns
        spawn_list: list[str] = []
        spawns = entities.Manager.floor_spawns(dungeon_floor)
        for n, spawn in enumerate(spawns):
            line_feed = '└' if n + 1 == len(spawns) else '├'
            spawn_list.append(f"> {line_feed} {spawn.title()}")
        spawn_text = '\n'.join(spawn_list)

        embed = discord.Embed(title=dungeon.name)
        embed.colour = discord.Colour.from_str("#00ff08")
        embed.set_footer(text=str(user.id))
        embed.description = f"**Current Location**: {dungeon_floor.name}\n\n" \
                            f"__**Area Information**__:\n" \
                            f"**Name**: {dungeon.name}\n" \
                            f"**Difficulty**: {dungeon.difficulty}\n" \
                            f"**Floor Difficulty**: {dungeon_floor.difficulty}\n" \
                            f"**Total Floors**: {dungeon.levels}\n" \
                            f"**Is Dungeon**: {str(dungeon.is_dungeon).lower()}\n\n" \
                            f"__**Connections:**__\n" \
                            f"{conn_text}\n\n" \
                            f"__**Current Floor Spawns:**__\n" \
                            f"{spawn_text}"

        return embed


class LocationView(ui.View):
    """User View that can be interacted with to make location."""

    def __init__(self, bot: discord.Client) -> None:
        self.bot = bot
        self.user: Optional[Union[discord.User, discord.Member]] = None
        super().__init__(timeout=None)

    def set_user(self, user: Union[discord.User, discord.Member]) -> None:
        """Sets the user so their locations can be used in the dropdown."""
        self.user = user
        user_l = users.Manager.get(user.id)
        self.add_item(LocationDropdown(user_l, Area))
        self.add_item(LocationDropdown(user_l, Level))

    @staticmethod
    def get_panel(user: Union[discord.User, discord.Member]) -> discord.Embed:
        """Gets the user stats for the user provided."""
        # Get the local user.
        user_l = users.Manager.get(user.id)
        c_location: str = 'Unknown'
        if user_l.c_location.name:
            c_location = user_l.c_location.name.replace("_", " ").title()

        # Build list of discovered locations.
        loc_text: list[str] = []
        locations = user_l.locations.get_unlocks()
        for n, loc in enumerate(locations):
            line_feed = '└' if n + 1 == len(locations) else '├'

            loc_name = "unknown"
            if loc.name:
                loc_name = loc.name.replace("_", " ").lower()

            current = ""
            if loc_name == c_location.lower():
                current = " (Current)"

            loc_text.append(f"> {line_feed} {loc_name.title()}{current}")
        full_text = '\n'.join(loc_text)

        # Get the list of connections.
        conn_text: list[str] = []
        conns = user_l.locations.connections(user_l.c_location)
        for n, loc in enumerate(conns):
            line_feed = '└' if n + 1 == len(conns) else '├'
            name = "Unknown"
            if loc.name:
                name = loc.name.replace("_", " ").title()
            conn_text.append(f"> {line_feed} {name}")
        conn_full = '\n'.join(conn_text)

        color = discord.Colour.from_str("#00ff08")
        desc = f"**{user}**\n\n" \
               f"**id**: {user.id}\n" \
               f"**level**: {user_l.level}\n" \
               f"**messages**: {user_l.msg_count}\n\n" \
               "> __**Areas Unlocked**__:\n" \
               f"**{full_text}**\n\n" \
               "> __**Area Connections**__:\n" \
               f"**{conn_full}**\n"

        embed = discord.Embed(description=desc, color=color)
        embed.set_footer(text=f"Current Location: {c_location}")
        embed.set_thumbnail(url=user.display_avatar.url)
        return embed


class UserStatsView(ui.View):
    """User View that can be interacted with to make user changes."""

    def __init__(self, bot: discord.Client) -> None:
        self.bot = bot
        self.user: Optional[Union[discord.User, discord.Member]] = None
        super().__init__(timeout=None)

    def set_user(self, user: Union[discord.User, discord.Member]) -> None:
        """Sets the user so their locations can be used in the dropdown."""
        self.user = user
        user_l = users.Manager.get(user.id)
        self.add_item(LocationDropdown(user_l, Area))
        self.add_item(LocationDropdown(user_l, Level))

    @staticmethod
    def get_panel(user: Union[discord.User, discord.Member]) -> discord.Embed:
        """Gets the user stats for the user provided."""
        # Get the local user.
        user_l = users.Manager.get(user.id)
        title = '' if user_l.button_press == 0 else ', the Button Presser'

        if user.bot:
            title = ', the Scholar'

        # Calculate the users age based on when they joined Discord.
        age = convert_age(user.created_at)

        powerhour_text = ""
        if user_l.is_powerhour:
            powerhour_text = "**powerhour**: enabled\n"

        weapon_name = "unarmed"
        if user_l.weapon:
            material = user_l.weapon.material
            dur = f"{user_l.weapon.uses} / {user_l.weapon.uses_max}"
            weapon_type = user_l.weapon._name.title()
            weapon_name = f"{material.name.replace('_', ' ')} " \
                          f"{weapon_type} [{dur}]"

        location_text: str = "Unknown"
        location = LocationsManager.get(user_l.c_location, user_l.c_floor)
        if location:
            location_text = location.name

        color = discord.Colour.from_str("#00ff08")
        desc = f"**{user}{title}**\n\n" \
               f"**id**: {user.id}\n" \
               f"**age**: {age}\n" \
               f"**deaths**: {user_l.deaths}\n" \
               f"**level**: {user_l.level}\n" \
               f"**gold**: {user_l.gold} gp\n" \
               f"**location**: {location_text}\n" \
               f"**weapon**: {weapon_name.lower()}\n" \
               f"**messages**: {user_l.msg_count}\n" \
               f"{powerhour_text}" \
               f"**gold multiplier**: {user_l.gold_multiplier :0.2f}\n\n" \
               "> __Gamble__:\n" \
               f"> ├ **total**: {user_l.gambles}\n" \
               f"> ├ **won**: {user_l.gambles_won}\n" \
               f"> ├ **win-rate**: {user_l.win_rate():0.2f}%\n" \
               f"> └ **minimum**: {user_l.minimum(20)} gp\n\n" \
               "> __Slaying__:\n" \
               f"> ├ **exp**: {user_l.exp}\n" \
               f"> ├ **total**: {user_l.monsters}\n" \
               f"> ├ **killed**: {user_l.kills}\n" \
               f"> └ **fled**: {max(user_l.monsters - user_l.kills, 0)}\n"

        c_location: str = 'Unknown'
        if user_l.c_location.name:
            c_location = user_l.c_location.name.title()
        embed = discord.Embed(description=desc, color=color)
        embed.set_footer(text=f"Current Location: {c_location}")
        embed.set_thumbnail(url=user.display_avatar.url)
        return embed


class InventoryView(ui.View):
    """Inventory View that can be interacted with to make item changes."""

    def __init__(self, bot: discord.Client) -> None:
        self.bot = bot
        self.inventory: Optional[Inventory] = None
        self.user: Optional[Union[discord.User, discord.Member]] = None
        super().__init__(timeout=None)

    def set_user(self, user: Union[discord.User, discord.Member],
                 inventory: Inventory) -> None:
        """Sets the user and inventory, so it can be used in the dropdown."""
        self.user = user
        self.add_item(InventorySellDropdown(inventory))
        self.add_item(InventoryUseDropdown(inventory))

        if len(inventory.get_bags()) > 0:
            user_l = users.Manager.get(user.id)
            self.add_item(InventoryShowDropdown(user_l, inventory.id))

    @staticmethod
    def get_panel(user: Union[discord.User, discord.Member],
                  inventory: Inventory) -> discord.Embed:
        """Gets the users inventory and converts to an embed."""
        # Get the local user.
        user_l = users.Manager.get(user.id)
        powerhour_status = "off"
        if user_l.is_powerhour:
            powerhour_status = "enabled"

        weapon_name = "unarmed"
        if user_l.weapon:
            material = user_l.weapon.material
            dur = f"{user_l.weapon.uses} / {user_l.weapon.uses_max}"
            weapon_type = user_l.weapon._name.title()
            weapon_name = f"{material.name.replace('_', ' ')} " \
                          f"{weapon_type} [{dur}]"

        # Get the contents of the inventory.
        inventory_str = show_inventory(inventory)

        # Users gold per message for a powerhour.
        gpm_ph = user_l.gold_multiplier + user_l.gold_multiplier_powerhour

        tree_list: list[str] = []
        c_inventory = inventory
        while c_inventory:
            tree_list.append(c_inventory.base_name)
            c_inventory = InventoryManager.get(c_inventory.parent_id)

        tree_list.reverse()
        tree = ' > '.join(tree_list)

        capacity_diff: int = inventory.max_capacity - inventory.base_capacity
        capacity_str: str = f"{inventory.max_capacity} " \
                            f"({inventory.base_capacity} +{capacity_diff})"

        bags_list: list[str] = []
        for n, bag in enumerate(inventory.get_bags()):
            line_feed = '└' if n + 1 == len(inventory.get_bags()) else '├'
            bags_list.append(f"> {line_feed} **{bag.name.title()}**")

        # If none, print none.
        bags_full = '\n'.join(bags_list)
        note: str = "**Note**: You can use the `[move` command to move items."
        if inventory.type == Inventory.Type.RESOURCES:
            bags_full = ""
            note = ""
        elif len(bags_list) == 0:
            bags_full = ""
        else:
            bags_full = f"__**Bags**__:\n{bags_full}\n\n"

        # Build the embed.
        embed = discord.Embed(title=tree)
        embed.colour = discord.Colour.from_str("#00ff08")
        embed.set_footer(text=f"{user.id}")
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.description = f"**gold**: {user_l.gold} gp\n" \
                            f"**gold per message (gpm)**: {user_l.gold_multiplier :0.2f}\n" \
                            f"**gpm (powerhour)**: {gpm_ph:0.2f}\n" \
                            f"**powerhour**: {powerhour_status}\n" \
                            f"**weapon**: {weapon_name.lower()}\n\n" \
                            f"**Bag**: {tree.title()}\n" \
                            f"**Bag Capacity**: {capacity_str}\n" \
                            f"**Stored Items**: {len(inventory.items)}\n" \
                            f"**Stored Value**: {inventory.value} gp\n\n" \
                            f"__**Items**__:\n" \
                            f"{inventory_str}\n\n" \
                            f"{bags_full}" \
                            f"{note}"
        return embed


class InventoryMoveView(ui.View):
    """Inventory View that can be interacted with to move items."""

    def __init__(self, bot: discord.Client) -> None:
        self.bot = bot
        self.inventory: Optional[Inventory] = None
        self.action: Optional[Union[Action, ItemMove]] = None
        self.user: Optional[Union[discord.User, discord.Member]] = None
        super().__init__(timeout=None)

    def set_user(self, user: Union[discord.User, discord.Member],
                 inventory: Inventory,
                 action: Optional[Action] = None) -> None:
        """Sets the user and inventory, so it can be used in the dropdown."""
        self.user = user
        if not action:
            self.action = ItemMove(user_id=user.id)
            ActionManager.add(self.action)
        else:
            self.action = action

        self.add_item(BagDropdown(user.id, "source"))
        self.add_item(ItemDropdown(user.id, inventory.id))
        self.add_item(BagDropdown(user.id, "destination"))
        self.add_item(ConfirmButton(Action.Types.ITEM_MOVE))
        self.add_item(CancelButton(Action.Types.ITEM_MOVE))

    @staticmethod
    def get_panel(user: Union[discord.User, discord.Member]) -> discord.Embed:
        """Gets the users inventory and converts to an embed."""
        source: str = "unset"
        destination: str = "unset"
        item_name: str = "unset"
        action = ActionManager.get(user.id, Action.Types.ITEM_MOVE)
        if action and isinstance(action, ItemMove):
            if action.source_id != "":
                bag = InventoryManager.get(action.source_id)
                source = bag.name if bag else "unknown"
            if action.destination_id != "":
                bag = InventoryManager.get(action.destination_id)
                destination = bag.name if bag else "unknown"
            if action.item_id != "":
                item = ItemManager.get(action.item_id)
                item_name = item.name if item else "unknown"

        embed = discord.Embed()
        embed.colour = discord.Colour.from_str("#00ff08")
        embed.title = "Item Relocation!"
        embed.description = "This tool is used to transfer an item from " \
                            "one bag to another bag.\n" \
                            "Where would you like to move the item?\n\n" \
                            f"> **Source**: {source}\n" \
                            f"> **Item**: {item_name}\n" \
                            f"> **Destination**: {destination}\n"
        embed.set_footer(text=f"{user.id}")
        return embed


class TradeView(ui.View):
    """Trade View that can be interacted with to give items to others."""

    def __init__(self, bot: discord.Client) -> None:
        self.bot = bot
        self.user: Optional[Union[discord.User, discord.Member]] = None
        super().__init__(timeout=None)

    def set_user(self, user: Union[discord.User, discord.Member]) -> None:
        """Sets the users involved in the trade."""
        self.user = user
        user_l = users.Manager.get(user.id)
        self.add_item(TradeDropdown(user_l.backpack))


async def setup(bot: discord.Client) -> None:
    """This is called by process that loads extensions."""
    bot.add_view(InspectView(bot))
    bot.add_view(UserStatsView(bot))
    bot.add_view(LocationView(bot))
    bot.add_view(InventoryView(bot))
    bot.add_view(InventoryMoveView(bot))
    bot.add_view(TradeView(bot))
