"""User based views."""
from typing import Optional
from datetime import datetime, timezone

import discord
from discord import ui

from dclient.helper import get_user
from managers import users
from managers.loot_tables import Material, Items


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


class BankDropdown(ui.Select):
    """Allows the user to select a new location."""

    def __init__(self, user: users.User) -> None:
        options: list[discord.SelectOption] = []

        all_label = f"All, value: {user.bank.value} gp"
        options.append(discord.SelectOption(label=all_label, value='1:1:all'))
        for item in user.bank.items:
            label: str = f"{item.name.title()}, value: {item.value} gp"
            value: str = f"{item.type}:{item.value}:{item.name}"
            options.append(discord.SelectOption(label=label, value=value))
        options.append(discord.SelectOption(label='None', value='1:0:none'))
        super().__init__(options=options,
                         placeholder="Sell items for gold.",
                         custom_id="user_bank_dropdown")

    async def callback(self, interaction: discord.Interaction):
        """Called when the menu is selected."""
        res = interaction.response
        if not interaction.message:
            return

        user = await extract_user(interaction.client, interaction.message)
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
            await res.send_message(f"Sold all items for **{total_value}** gp!")
            return

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

        await res.send_message(f"You sold **{item.name.title()}** for "
                               f"value: {item.value} gp")


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
    def get_panel(user: discord.User) -> discord.Embed:
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
        if user_l.weapon > Material.NONE:
            material = Material(user_l.weapon)
            dur = f"{user_l.weapon_durability} / {user_l.weapon * 2}"
            wtype = user_l.weapon_name.title()
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
        self.user: Optional[discord.User] = None
        super().__init__(timeout=None)

    def set_user(self, user: discord.User) -> None:
        """Sets the user so their bank can be used in the dropdown."""
        self.user = user
        user_l = users.Manager.get(user.id)
        self.add_item(BankDropdown(user_l))

    @staticmethod
    def get_panel(user: discord.User) -> discord.Embed:
        """Gets the users bank for the user provided."""
        # Get the local user.
        user_l = users.Manager.get(user.id)
        title = '' if user_l.button_press == 0 else ', the Button Presser'

        if user.bot:
            title = ', the Scholar'

        # Create a list of items.
        items: list[str] = []
        for n, item in enumerate(user_l.bank.items):
            lfeed = '└' if n + 1 == len(user_l.bank.items) else '├'
            items.append(f"> {lfeed} **{item.name.title()}**, "
                         f"value: {item.value} gp")

        # If none, print none.
        items_full = '\n'.join(items)
        if len(items) == 0:
            items_full = '> └ **none**'

        # Build the embed.
        embed = discord.Embed()
        embed.color = discord.Colour.from_str("#00ff08")
        embed.set_footer(text=f"{user.id}")
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.description = f"**{user}{title}**\n\n"\
            f"**id**: {user.id}\n"\
            f"**gold**: {user_l.gold} gp\n\n"\
            f"**Bank Capacity**: {user_l.bank.capacity}\n"\
            f"**Banked Items**: {len(user_l.bank.items)}\n\n"\
            f"__**Items**__:\n"\
            f"{items_full}\n\n"\
            f"**__Total Value__: {user_l.bank.value} gp**"
        return embed


async def setup(bot: discord.Client) -> None:
    """This is called by process that loads extensions."""
    bot.add_view(UserView(bot))
    bot.add_view(BankView(bot))
