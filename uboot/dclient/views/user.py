"""User based views."""
from datetime import datetime, timezone
from typing import Optional, Union, Type

import discord
from discord import ui

from dclient.helper import get_user
from managers import users
from managers.banks import Inventory
from managers.locations import Area, Level, Manager as LocationsManager
from managers.logs import Log
from managers.loot_tables import Items


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
        elif item.type == Items.BAG:
            left = "slots: "
            value = ""
        elif item.is_consumable:
            left = "charges: "
        elif item.is_usable:
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


class InventoryShowDropdown(ui.Select):
    """Allows the user to see a specific inventory."""

    def __init__(self, user: users.User) -> None:
        options: list[discord.SelectOption] = []

        for bag in user.bank.bags:
            label: str = f"{bag.name.title()}, value: {bag.value} gp"
            value: str = f"{bag.type}:{bag.value}:{bag.name}"
            options.append(discord.SelectOption(label=label, value=value))
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
            return await res.send_message("You cannot view another users items.",
                                          ephemeral=True,
                                          delete_after=20)

        # Extract the item.
        user_l = users.Manager.get(interaction.user.id)
        bag_parse = self.values[0].split(':')
        bag_type = int(bag_parse[0])
        value = int(bag_parse[1])
        name = bag_parse[2]

        # Find the bag.
        bag = user_l.bank.get_bag(bag_type, value, name)
        if not bag:
            await res.send_message("Could not find bag. Do you still own it?",
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
            return await res.send_message("You cannot sell another users items.",
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
        view.set_user(user, self.inventory)

        # Check if we are selling all items.
        if item_id == "all":
            total_value = self.inventory.value
            user_l.gold += total_value
            user_l.save()

            self.inventory.items = {}
            user_l.bank.save()

            Log.player(f"{user} sold all items for {total_value} gp!",
                       guild_id=guild.id, user_id=user.id)

            ephemeral: bool = True
            delete_after: Optional[int] = 30
            try:
                embed = InventoryView.get_panel(user, self.inventory)
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
                user_l.save()
            user_l.bank.save()
        else:
            value = item.value
            # Remove the item from the user.
            if self.inventory.remove_item(item.id):
                user_l.gold += value
                user_l.save()
                user_l.bank.save()

        Log.player(f"{user} sold {quantity}{item.name.title()} for {value} gp.",
                   guild_id=guild.id, user_id=user.id)

        ephemeral: bool = True
        delete_after: Optional[int] = 30
        try:
            embed = InventoryView.get_panel(user, self.inventory)
            await msg.edit(embed=embed, view=view)
            ephemeral = False
            delete_after = None
        except BaseException:
            pass

        await res.send_message(f"{user} sold {quantity}**{item.name.title()}** "
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
            label: str = f"{item.name.title()} [{item.uses} / {item.uses_max}]"
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
            return await res.send_message("You cannot use another users items.",
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
        view.set_user(user, self.inventory)

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
                user_l.save()
            user_l.bank.save()

            Log.player(f"{user} {use_text} {item.name.title()}, {granting}.",
                       guild_id=guild.id, user_id=user.id)

            ephemeral: bool = True
            delete_after: Optional[int] = 30
            try:
                embed = InventoryView.get_panel(user, self.inventory)
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
        if self.inventory.remove_item(item_id):
            # Swap the weapon out.
            if item.type == Items.WEAPON:
                use_text = "equipped"
                if user_l.weapon:
                    self.inventory.add_item(user_l.weapon)
                user_l.weapon = item
                user_l.save()
            user_l.bank.save()

        Log.player(f"{user} {use_text} {item.name.title()}",
                   guild_id=guild.id, user_id=user.id)

        ephemeral: bool = True
        delete_after: Optional[int] = 30
        try:
            embed = InventoryView.get_panel(user, self.inventory)
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
            value: int = item.value
            if item.is_consumable:
                value = item.base_value
            label: str = f"{item.name.title()}, value: {value} gp"
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
                to_user.bank.add_item(item, uses_override=1, max_override=True)

            if item.uses == 0:
                self.inventory.remove_item(item.id)
            user_l.bank.save()
            to_user.bank.save()
        else:
            # Remove the item from the user.
            if self.inventory.remove_item(item.id):
                user_l.bank.save()
                to_user.bank.add_item(item, max_override=True)
                to_user.bank.save()

        value = item.base_value if item.is_consumable else item.value

        log_text = f"{user} gave {quantity}**{item.name.title()}** "\
            f"(value: {value} gp) to {extracted_users[1]}."
        Log.player(log_text.replace('*', ''), guild_id=guild.id, user_id=user.id)
        Log.player(f"{extracted_users[1]} received {quantity}"
                   f"{item.name.title()} (value: {value} gp) from {user}.",
                   guild_id=guild.id, user_id=extracted_users[1].id)

        view = TradeView(interaction.client)
        view.set_user(user)

        embed = InventoryView.get_panel(user, self.inventory)
        embed.set_footer(text=f"{user_l.id}:{to_user.id}")
        await msg.edit(embed=embed, view=view)
        await res.send_message(log_text)


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
                name = loc.name.title()
            conn_text.append(f"> {line_feed} {name}")
        conn_full = '\n'.join(conn_text)

        color = discord.Colour.from_str("#00ff08")
        desc = f"**{user}**\n\n"\
            f"**id**: {user.id}\n"\
            f"**level**: {user_l.level}\n"\
            f"**messages**: {user_l.msg_count}\n\n"\
            "> __**Areas Unlocked**__:\n"\
            f"**{full_text}**\n\n"\
            "> __**Area Connections**__:\n"\
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
        age = datetime.now(timezone.utc) - user.created_at
        year_str = '' if age.days // 365 < 1 else f"{age.days//365} year(s), "
        day_str = '' if age.days % 365 == 0 else f"{int(age.days%365)} day(s)"

        powerhour_text = ""
        if user_l.is_powerhour:
            powerhour_text = "**powerhour**: enabled\n"

        weapon_name = "unarmed"
        if user_l.weapon:
            material = user_l.weapon.material
            dur = f"{user_l.weapon.uses} / {user_l.weapon.uses_max}"
            weapon_type = user_l.weapon._name.title()
            weapon_name = f"{material.name.replace('_', ' ')} {weapon_type} [{dur}]"

        location_text: str = "Unknown"
        location = LocationsManager.get(user_l.c_location, user_l.c_floor)
        if location:
            location_text = location.name

        color = discord.Colour.from_str("#00ff08")
        desc = f"**{user}{title}**\n\n"\
            f"**id**: {user.id}\n"\
            f"**age**: {year_str}{day_str}\n"\
            f"**deaths**: {user_l.deaths}\n"\
            f"**level**: {user_l.level}\n"\
            f"**gold**: {user_l.gold} gp\n"\
            f"**location**: {location_text}\n"\
            f"**weapon**: {weapon_name.lower()}\n"\
            f"**messages**: {user_l.msg_count}\n"\
            f"{powerhour_text}"\
            f"**gold multiplier**: {user_l.gold_multiplier :0.2f}\n\n"\
            "> __Gamble__:\n"\
            f"> ├ **total**: {user_l.gambles}\n"\
            f"> ├ **won**: {user_l.gambles_won}\n"\
            f"> ├ **win-rate**: {user_l.win_rate():0.2f}%\n"\
            f"> └ **minimum**: {user_l.minimum(20)} gp\n\n"\
            "> __Slaying__:\n"\
            f"> ├ **exp**: {user_l.exp}\n"\
            f"> ├ **total**: {user_l.monsters}\n"\
            f"> ├ **killed**: {user_l.kills}\n"\
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
        user_l = users.Manager.get(user.id)
        self.add_item(InventorySellDropdown(inventory))
        self.add_item(InventoryUseDropdown(inventory))

        # Only banks can show their sub containers for now.
        if inventory.type == Inventory.Type.BANK:
            self.add_item(InventoryShowDropdown(user_l))

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
            weapon_name = f"{material.name.replace('_', ' ')} {weapon_type} [{dur}]"

        # Get the contents of the inventory.
        inventory_str = show_inventory(inventory)

        # Users gold per message for a powerhour.
        gpm_ph = user_l.gold_multiplier + user_l.gold_multiplier_powerhour

        tree_list: list[str] = []
        c_inventory = inventory
        while c_inventory:
            tree_list.append(c_inventory.name)
            c_inventory = c_inventory.parent

        tree_list.reverse()
        tree = ' > '.join(tree_list)

        capacity_diff: int = inventory.max_capacity - inventory.base_capacity
        capacity_str: str = f"{inventory.max_capacity} "\
            f"({inventory.base_capacity} +{capacity_diff})"

        # Build the embed.
        embed = discord.Embed(title=tree)
        embed.colour = discord.Colour.from_str("#00ff08")
        embed.set_footer(text=f"{user.id}")
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.description = f"**gold**: {user_l.gold} gp\n"\
            f"**gold per message (gpm)**: {user_l.gold_multiplier :0.2f}\n"\
            f"**gpm (powerhour)**: {gpm_ph:0.2f}\n"\
            f"**powerhour**: {powerhour_status}\n"\
            f"**weapon**: {weapon_name.lower()}\n\n"\
            f"**Bag**: {tree}\n"\
            f"**Bag Capacity**: {capacity_str}\n"\
            f"**Stored Items**: {len(inventory.items)}\n"\
            f"**Stored Value**: {inventory.value} gp\n\n"\
            f"__**Items**__:\n"\
            f"{inventory_str}"
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
        self.add_item(TradeDropdown(user_l.bank))


async def setup(bot: discord.Client) -> None:
    """This is called by process that loads extensions."""
    bot.add_view(UserStatsView(bot))
    bot.add_view(InventoryView(bot))
    bot.add_view(TradeView(bot))
