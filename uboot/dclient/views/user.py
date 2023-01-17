"""User based views."""
from typing import Optional, Union
from datetime import datetime, timezone

import discord
from discord import ui

from dclient.helper import get_user
from managers import users
from managers.loot_tables import Items
from managers.logs import Log


async def extract_user(client: discord.Client,
                       message: discord.Message) -> Optional[discord.User]:
    """Attempt to get the user from a message with an embed."""
    # Get the embed to extract the user id.
    if len(message.embeds) == 0:
        return None

    # Extract the user id from the footer.
    user_id: int = 0
    try:
        if message.embeds[0].footer.text:
            user_id = int(message.embeds[0].footer.text)
    except BaseException:
        pass

    # Lookup the user
    return await get_user(client, user_id)


class LocationDropdown(ui.Select):
    """Allows the user to select a new location."""

    def __init__(self, user: users.User) -> None:
        options: list[discord.SelectOption] = []
        for location in user.locations.get_unlocks():
            options.append(discord.SelectOption(label=location))
        super().__init__(options=options,
                         placeholder="Recall to a new location.",
                         custom_id="user_location_dropdown")

    async def callback(self, interaction: discord.Interaction):
        """Called when the menu is selected."""
        res = interaction.response

        # Changes the users location, only if it is discovered.
        user = users.Manager.get(interaction.user.id)
        changed = user.change_location(self.values[0])
        if interaction.message and isinstance(interaction.user, discord.User):
            embed = UserView.get_panel(interaction.user)
            await interaction.message.edit(embed=embed)

        if not changed:
            await res.send_message("Unknown location, have you discovered it?",
                                   ephemeral=True,
                                   delete_after=30)
            return

        user.save()
        await res.send_message(f"Location set to {self.values[0].title()}.",
                               ephemeral=True,
                               delete_after=30)


class BankSellDropdown(ui.Select):
    """Allows the user to select an item to sell."""

    def __init__(self, user: users.User) -> None:
        options: list[discord.SelectOption] = []

        all_label = f"All Items, value: {user.bank.value} gp"
        options.append(discord.SelectOption(label=all_label, value='1:1:all'))
        for item in user.bank.items:
            label: str = f"{item.name.title()}, value: {item.value} gp"
            value: str = f"{item.type}:{item.value}:{item.name}"
            options.append(discord.SelectOption(label=label, value=value))
        options.append(discord.SelectOption(label='None', value='1:0:none'))
        super().__init__(options=options,
                         placeholder="Sell Items",
                         custom_id="user_bank_sell_dropdown")

    async def callback(self, interaction: discord.Interaction):
        """Called when the menu is selected."""
        res = interaction.response
        msg = interaction.message
        guild = interaction.guild
        if not msg or not guild:
            return

        user = await extract_user(interaction.client, msg)
        if not user:
            await res.send_message("User could not be identified.",
                                   ephemeral=True,
                                   delete_after=20)
            return

        if interaction.user != user:
            await res.send_message("You cannot sell another users items.",
                                   ephemeral=True,
                                   delete_after=20)
            return

        # Extract the item.
        user_l = users.Manager.get(interaction.user.id)
        item_parse = self.values[0].split(':')
        itype = int(item_parse[0])
        ivalue = int(item_parse[1])
        iname = item_parse[2]

        # None selected.
        if Items(itype) == Items.NONE and ivalue == 0:
            await res.send_message("Transaction cancelled.",
                                   ephemeral=True,
                                   delete_after=20)
            return

        # Check if we are selling all items.
        if Items(itype) == Items.NONE and ivalue > 0:
            total_value = user_l.bank.value
            user_l.gold += total_value
            user_l.save()

            user_l.bank.items = []
            user_l.bank.save()

            Log.player(f"{user} sold all items for {total_value} gp!",
                       guild_id=guild.id, user_id=user.id)

            # Update the view.
            view = BankView(interaction.client)
            view.set_user(user)
            await msg.edit(embed=BankView.get_panel(user), view=view)

            return await res.send_message(f"{user} sold all items "
                                          f"for **{total_value}** gp!")

        # Find the item.
        item = next((i for i in user_l.bank.items if i.type == itype and
                     i.value == ivalue and i.name == iname), None)
        if not item:
            await res.send_message("Could not find item. Do you still own it?",
                                   ephemeral=True,
                                   delete_after=20)
            return

        # Remove the item from the user.
        if user_l.bank.remove_item(Items(itype), iname, ivalue):
            user_l.gold += ivalue
            user_l.save()
            user_l.bank.save()

            Log.player(f"{user} sold {item.name.title()} for {item.value} gp.",
                       guild_id=guild.id, user_id=user.id)

        # Update the view.
        view = BankView(interaction.client)
        view.set_user(user)
        await msg.edit(embed=BankView.get_panel(user), view=view)

        await res.send_message(f"{user} sold **{item.name.title()}** "
                               f"for {item.value} gp.")


class BankUseDropdown(ui.Select):
    """Allows the user to select an item to use."""

    def __init__(self, user: users.User) -> None:
        options: list[discord.SelectOption] = []

        for item in user.bank.items:
            if not item.isusable:
                continue
            label: str = f"{item.name.title()} [{item.uses} / {item.uses_max}]"
            value: str = f"{item.type}:{item.value}:{item.name}"
            options.append(discord.SelectOption(label=label, value=value))
        options.append(discord.SelectOption(label='None', value='1:0:none'))
        super().__init__(options=options,
                         placeholder="Use / Equip Item",
                         custom_id="user_bank_use_dropdown")

    async def callback(self, interaction: discord.Interaction):
        """Called when the menu is selected."""
        res = interaction.response
        msg = interaction.message
        guild = interaction.guild
        if not msg or not guild:
            return

        user = await extract_user(interaction.client, msg)
        if not user:
            await res.send_message("User could not be identified.",
                                   ephemeral=True,
                                   delete_after=20)
            return

        if interaction.user != user:
            await res.send_message("You cannot use another users items.",
                                   ephemeral=True,
                                   delete_after=20)
            return

        # Extract the item.
        user_l = users.Manager.get(interaction.user.id)
        item_parse = self.values[0].split(':')
        itype = int(item_parse[0])
        ivalue = int(item_parse[1])
        iname = item_parse[2]

        # None selected.
        if Items(itype) == Items.NONE and ivalue == 0:
            await res.send_message("No item used.",
                                   ephemeral=True,
                                   delete_after=20)
            return

        # Find the item.
        item = user_l.bank.get_item(Items(itype), iname, ivalue)
        if not item:
            await res.send_message("Could not find item. Do you still own it?",
                                   ephemeral=True,
                                   delete_after=20)
            return

        use_text = "used"

        if item.isconsumable and user_l.bank.use_consumable(item):
            granting: str = "granting a powerhour"
            if item.type == Items.POWERHOUR:
                user_l.powerhour = datetime.now()
            if item.uses == 0:
                user_l.bank.remove_item(item.type, item.name, item.value)
                user_l.save()
            user_l.bank.save()

            Log.player(f"{user} {use_text} {item.name.title()}, {granting}.",
                       guild_id=guild.id, user_id=user.id)

            view = BankView(interaction.client)
            view.set_user(user)
            await msg.edit(embed=BankView.get_panel(user), view=view)
            return await res.send_message(f"{user} {use_text} "
                                          f"**{item.name.title()}**, "
                                          f"{granting}.")

        # Remove the item from the user.
        if user_l.bank.remove_item(Items(itype), iname, ivalue):
            # Swap the weapon out.
            if item.type == Items.WEAPON:
                use_text = "equipped"
                if user_l.weapon:
                    user_l.bank.add_item(user_l.weapon)
                user_l.weapon = item
                user_l.save()
            user_l.bank.save()

        Log.player(f"{user} {use_text} {item.name.title()}",
                   guild_id=guild.id, user_id=user.id)

        view = BankView(interaction.client)
        view.set_user(user)
        await msg.edit(embed=BankView.get_panel(user), view=view)
        await res.send_message(f"{user} {use_text} **{item.name.title()}**.")


class UserView(ui.View):
    """User View that can be interacted with to make user changes."""

    def __init__(self, bot: discord.Client) -> None:
        self.bot = bot
        self.user: Optional[discord.User] = None
        super().__init__(timeout=None)

    def set_user(self, user: discord.User) -> None:
        """Sets the user so their locations can be used in the dropdown."""
        self.user = user
        user_l = users.Manager.get(user.id)
        self.add_item(LocationDropdown(user_l))

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
        if user_l.powerhour:
            powerhour_text = "**powerhour**: enabled\n"

        weapon_name = "unarmed"
        if user_l.weapon:
            material = user_l.weapon.material
            dur = f"{user_l.weapon.uses} / {user_l.weapon.uses_max}"
            wtype = user_l.weapon._name.title()
            weapon_name = f"{material.name.replace('_', ' ')} {wtype} [{dur}]"

        color = discord.Colour.from_str("#00ff08")
        desc = f"**{user}{title}**\n\n"\
            f"**id**: {user.id}\n"\
            f"**age**: {year_str}{day_str}\n"\
            f"**deaths**: {user_l.deaths}\n"\
            f"**level**: {user_l.level}\n"\
            f"**gold**: {user_l.gold} gp\n"\
            f"**weapon**: {weapon_name.lower()}\n"\
            f"**messages**: {user_l.msg_count}\n"\
            f"{powerhour_text}"\
            f"**gold multiplier**: {(user_l.gold_multiplier):0.2f}\n\n"\
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


class BankView(ui.View):
    """Bank View that can be interacted with to make item changes."""

    def __init__(self, bot: discord.Client) -> None:
        self.bot = bot
        self.user: Optional[Union[discord.User, discord.Member]] = None
        super().__init__(timeout=None)

    def set_user(self, user: Union[discord.User, discord.Member]) -> None:
        """Sets the user so their bank can be used in the dropdown."""
        self.user = user
        user_l = users.Manager.get(user.id)
        self.add_item(BankSellDropdown(user_l))
        self.add_item(BankUseDropdown(user_l))

    @staticmethod
    def get_panel(user: Union[discord.User, discord.Member]) -> discord.Embed:
        """Gets the users bank for the user provided."""
        # Get the local user.
        user_l = users.Manager.get(user.id)
        title = '' if user_l.button_press == 0 else ', the Button Presser'

        if user.bot:
            title = ', the Scholar'

        powerhour_status = "off"
        if user_l.powerhour:
            powerhour_status = "enabled"

        weapon_name = "unarmed"
        if user_l.weapon:
            material = user_l.weapon.material
            dur = f"{user_l.weapon.uses} / {user_l.weapon.uses_max}"
            wtype = user_l.weapon._name.title()
            weapon_name = f"{material.name.replace('_', ' ')} {wtype} [{dur}]"

        # Create a list of items.
        items: list[str] = []
        for n, item in enumerate(user_l.bank.items):
            lfeed = '└' if n + 1 == len(user_l.bank.items) else '├'
            left: str = ""
            if item.isconsumable:
                left = "charges: "
            elif item.isusable:
                left = "durability: "
            uses = f" [{left}{item.uses} / {item.uses_max}]" if item.isusable else ""
            items.append(f"> {lfeed} **{item.name.title()}**{uses}, "
                         f"value: {item.value} gp")

        # If none, print none.
        items_full = '\n'.join(items)
        if len(items) == 0:
            items_full = '> └ **none**'

        # Users gold per message for a powerhour.
        gpm_ph = user_l.gold_multiplier + user_l.gold_multiplier_powerhour

        # Build the embed.
        embed = discord.Embed()
        embed.color = discord.Colour.from_str("#00ff08")
        embed.set_footer(text=f"{user.id}")
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.description = f"**{user}{title}**\n\n"\
            f"**id**: {user.id}\n"\
            f"**gold**: {user_l.gold} gp\n"\
            f"**gold per message (gpm)**: {(user_l.gold_multiplier):0.2f}\n"\
            f"**gpm (powerhour)**: {gpm_ph:0.2f}\n"\
            f"**powerhour**: {powerhour_status}\n"\
            f"**weapon**: {weapon_name.lower()}\n\n"\
            f"**Bank Capacity**: {user_l.bank.capacity}\n"\
            f"**Banked Items**: {len(user_l.bank.items)}\n"\
            f"**Banked Value**: {user_l.bank.value} gp\n\n"\
            f"__**Items**__:\n"\
            f"{items_full}"
        return embed


async def setup(bot: discord.Client) -> None:
    """This is called by process that loads extensions."""
    bot.add_view(UserView(bot))
    bot.add_view(BankView(bot))
