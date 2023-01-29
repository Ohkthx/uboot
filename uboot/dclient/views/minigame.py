"""User based views."""
from datetime import datetime, timedelta
from random import choice, randint
from enum import Enum
from typing import Optional

import discord
from discord import ui

from dclient import DiscordBot
from dclient.helper import get_user, check_minigame
from dclient.destructable import Destructable, DestructableManager
from dclient.views.user import (InventoryView, LocationView, UserStatsView)
from managers import users, entities
from managers.logs import Log
from managers.loot_tables import Item, Items, Material, Reagent


async def update_footer(message: discord.Message, updates: str) -> None:
    """Attempts to update the footer of a message with new text."""
    if len(message.embeds) == 0:
        return

    embed = message.embeds[0]
    embed.set_footer(text=updates)
    await message.edit(embed=embed)


def extract_ints(message: discord.Message) -> list[int]:
    """Attempt to get integers from a message with an embed."""
    # Get the embed to extract the integers.
    if len(message.embeds) == 0:
        return []

    # Extract the integerss from the footer.
    all_ints: list[int] = []
    try:
        if message.embeds[0].footer.text:
            raw_ids = message.embeds[0].footer.text.split(':')
            all_ints = [int(extracted_int) for extracted_int in raw_ids]
    except BaseException:
        pass

    return all_ints


async def extract_users(client: discord.Client,
                        message: discord.Message) -> list[discord.User]:
    """Attempt to extract user ids from a messages embed."""
    user_ids = extract_ints(message)

    # Lookup the users
    extracted_users: list[discord.User] = []
    for user_id in user_ids:
        user = await get_user(client, user_id)
        if user:
            extracted_users.append(user)
    return extracted_users


class ManageOptions(Enum):
    STATS = "view STATS"
    BANK = "check BANK"
    RESOURCES = "check RESOURCES"
    RECALL = "perform RECALL"


class ManagementDropdown(ui.Select):
    """Allows the user to select an item to manage."""

    def __init__(self) -> None:
        options: list[discord.SelectOption] = []

        for opt in ManageOptions:
            options.append(discord.SelectOption(
                label=opt.value, value=opt.name))

        super().__init__(options=options,
                         placeholder="Pick an action to perform.",
                         custom_id="management_dropdown")

    async def callback(self, interaction: discord.Interaction):
        """Called when the menu is selected."""
        res = interaction.response
        guild = interaction.guild
        user = interaction.user
        message = interaction.message
        if not guild or not isinstance(user, discord.Member) or not message:
            return

        thread = interaction.channel
        if not thread or not isinstance(thread, discord.Thread):
            return

        # Check that the user has the minigame role.
        passed, msg = await check_minigame(interaction.client, user, guild.id)
        if not passed:
            return await res.send_message(msg, ephemeral=True, delete_after=30)

        # Remove the old views.
        category = Destructable.Category.OTHER
        await DestructableManager.remove_many(user.id, True, category)

        option: ManageOptions = ManageOptions.STATS
        for opt in ManageOptions:
            if opt.name.upper() == self.values[0].upper():
                option = opt

        user_l = users.Manager.get(user.id)
        stats = extract_ints(message)

        # Get the proper view for the sub menu.
        view: Optional[ui.View] = None
        embed: Optional[discord.Embed] = None
        if option == ManageOptions.BANK:
            stats[1] += 1
            view = InventoryView(interaction.client)
            view.set_user(user, user_l.bank)
            embed = InventoryView.get_panel(user, user_l.bank)
        elif option == ManageOptions.RESOURCES:
            stats[2] += 1
            view = InventoryView(interaction.client)
            view.set_user(user, user_l.bank.resources)
            embed = InventoryView.get_panel(user, user_l.bank.resources)
        elif option == ManageOptions.RECALL:
            stats[3] += 1
            view = LocationView(interaction.client)
            view.set_user(user)
            embed = LocationView.get_panel(user)
        else:
            stats[0] += 1
            view = UserStatsView(interaction.client)
            view.set_user(user)
            embed = UserStatsView.get_panel(user)

        # Submit the changes.
        stats_changes = ':'.join([str(i) for i in stats])
        await update_footer(message, stats_changes)
        await res.send_message(embed=embed, view=view, ephemeral=True,
                               delete_after=60)


class UserManagementView(ui.View):
    """Basic user actions for managing their character."""

    def __init__(self, bot: discord.Client) -> None:
        self.bot = bot
        super().__init__(timeout=None)
        self.add_item(ManagementDropdown())

    @staticmethod
    def get_panel() -> discord.Embed:
        """Creates the panels embed for the basic action view."""
        embed = discord.Embed()
        embed.color = discord.Colour.from_str("#00ff08")
        embed.description = "Manage your user account below.\n\n"\
            f"__**Options**__:\n"\
            f"> ├ **STATS**, check your player status.\n"\
            f"> ├ **BANK**, manage your bank and sell items.\n"\
            f"> ├ **RESOURCES**, manage your resources.\n"\
            f"> └ **RECALL**, travel to a new location.\n"
        embed.set_footer(text="0:0:0:0")

        return embed


class ResourceView(ui.View):
    """Creates a new taunt panel."""

    def __init__(self, bot: discord.Client) -> None:
        self.bot = bot
        super().__init__(timeout=None)

    @staticmethod
    def get_panel() -> discord.Embed:
        """Creates the panels embed for the resource view."""
        embed = discord.Embed(title="Fill your bank with loot or resources!")
        embed.color = discord.Colour.from_str("#00ff08")
        embed.description = "Interested in adventure?\nAre you brave?\n"\
            f"Trying to farm for new weapons, armor, or materials?\n\n"\
            f"__**Options**__:\n"\
            f"> ├ **TAUNT**, attempt to attract nearby enemies.\n"\
            f"> ├ **FORAGE**, try to find new reagents.\n"\
            f"> └ **MINE**, swing your pickaxe to strike riches.\n\n"\
            "**Note**: These actions can place you into combat."
        embed.set_footer(text="0:0:0:0:0:0:0:0:0")

        return embed

    @ui.button(label='👺 TAUNT', style=discord.ButtonStyle.red,
               custom_id='resource_view:taunt')
    async def taunt(self, interaction: discord.Interaction, button: ui.Button):
        """Taunts entities to attack the player who pressed the button."""
        res = interaction.response
        guild = interaction.guild
        author = interaction.user
        message = interaction.message
        if not guild or not isinstance(author, discord.Member) or not message:
            return

        thread = interaction.channel
        if not thread or not isinstance(thread, discord.Thread):
            return

        # Check that the user has the minigame role.
        passed, msg = await check_minigame(self.bot, author, guild.id)
        if not passed:
            return await res.send_message(msg, ephemeral=True, delete_after=30)

        stats = extract_ints(message)

        # Prevent taunt spam.
        user_l = users.Manager.get(author.id)
        if not user_l.timer_expired(users.Cooldown.TAUNT):
            timediff = datetime.now() - user_l.cooldown(users.Cooldown.TAUNT)
            minutes = (timedelta(minutes=12) - timediff) / timedelta(minutes=1)

            stats[2] += 1
            stats_changes = ':'.join([str(i) for i in stats])
            await update_footer(message, stats_changes)
            return await res.send_message("You are tired and cannot taunt for "
                                          f"another {minutes:0.1f} minutes.",
                                          ephemeral=True,
                                          delete_after=30)

        # Check if the user is in combat.
        if user_l.incombat:
            return await res.send_message("You are already in combat with "
                                          "another creature.",
                                          ephemeral=True,
                                          delete_after=30)

        if not isinstance(self.bot, DiscordBot):
            return await res.send_message("Could not get powerhour status",
                                          ephemeral=True,
                                          delete_after=30)

        stats[0] += 1

        # Update with a new taunt attempt.
        user_l.mark_cooldown(users.Cooldown.TAUNT)

        # Spawn the creature.
        loc = user_l.c_location
        difficulty = user_l.difficulty
        inpowerhour = self.bot.powerhours.get(guild.id)
        entity = entities.Manager.check_spawn(loc, difficulty,
                                              inpowerhour is not None,
                                              user_l.ispowerhour,
                                              True)
        if not entity:
            stats_changes = ':'.join([str(i) for i in stats])
            await update_footer(message, stats_changes)
            return await res.send_message("No nearby enemies react to your "
                                          "taunt.",
                                          ephemeral=True,
                                          delete_after=30)

        stats[1] += 1
        stats_changes = ':'.join([str(i) for i in stats])
        await update_footer(message, stats_changes)
        message = await thread.send(content="Your taunt attracted "
                                    f"**{entity.name}**!",
                                    delete_after=30)

        if not message:
            Log.error("Could not get message from successful taunt button.",
                      guild_id=guild.id)
            return

        try:
            await self.bot.add_entity(message, author, entity)
        except BaseException as exc:
            Log.error(f"Error while processing taunt button, {exc}")

    @ui.button(label='🪴 FORAGE', style=discord.ButtonStyle.green,
               custom_id='resource_view:forage')
    async def forage(self, interaction: discord.Interaction, button: ui.Button):
        """Attempts to discover new reagents."""
        res = interaction.response
        guild = interaction.guild
        author = interaction.user
        message = interaction.message
        if not guild or not isinstance(author, discord.Member) or not message:
            return

        thread = interaction.channel
        if not thread or not isinstance(thread, discord.Thread):
            return

        # Check that the user has the minigame role.
        passed, msg = await check_minigame(self.bot, author, guild.id)
        if not passed:
            return await res.send_message(msg, ephemeral=True, delete_after=30)

        stats = extract_ints(message)

        # Prevent forage spam.
        user_l = users.Manager.get(author.id)
        if not user_l.timer_expired(users.Cooldown.FORAGE):
            timediff = datetime.now() - user_l.cooldown(users.Cooldown.FORAGE)
            minutes = (timedelta(minutes=5) - timediff) / timedelta(minutes=1)

            stats[5] += 1
            stats_changes = ':'.join([str(i) for i in stats])
            await update_footer(message, stats_changes)
            return await res.send_message("You are tired and cannot forage for "
                                          f"another {minutes:0.1f} minutes.",
                                          ephemeral=True,
                                          delete_after=30)

        # Forage was successful, attempt to get some resources.
        stats[3] += 1

        # Update with a new forage attempt.
        user_l.mark_cooldown(users.Cooldown.FORAGE)

        reagent = Reagent(randint(Reagent.BLACK_PEARL, Reagent.SULFUROUS_ASH))
        count = choice([0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 2, 2, 3])
        if count == 0:
            stats_changes = ':'.join([str(i) for i in stats])
            await update_footer(message, stats_changes)
            return await res.send_message("You fail to forage any reagents.",
                                          ephemeral=True,
                                          delete_after=30)

        stats[4] += 1
        stats_changes = ':'.join([str(i) for i in stats])
        await update_footer(message, stats_changes)
        item = Item(Items.REAGENT,
                    material=reagent,
                    value=5,
                    uses=count,
                    uses_max=6)

        user_l.bank.add_item(item)
        user_l.bank.save()

        try:
            return await res.send_message(f"You found **{count} "
                                          f"{item.name.lower()}** while "
                                          "foraging!",
                                          ephemeral=True,
                                          delete_after=30)
        except BaseException as exc:
            Log.player(f"{author} could not complete foraging order, {exc}",
                       guild_id=guild.id, user_id=author.id)

    @ui.button(label='⛏️ MINE', style=discord.ButtonStyle.blurple,
               custom_id='resource_view:mine')
    async def mine(self, interaction: discord.Interaction, button: ui.Button):
        """Attempts to discover new ores."""
        res = interaction.response
        guild = interaction.guild
        author = interaction.user
        message = interaction.message
        if not guild or not isinstance(author, discord.Member) or not message:
            return

        thread = interaction.channel
        if not thread or not isinstance(thread, discord.Thread):
            return

        # Check that the user has the minigame role.
        passed, msg = await check_minigame(self.bot, author, guild.id)
        if not passed:
            return await res.send_message(msg, ephemeral=True, delete_after=30)

        stats = extract_ints(message)

        # Prevent mining spam.
        user_l = users.Manager.get(author.id)
        if not user_l.timer_expired(users.Cooldown.MINING):
            timediff = datetime.now() - user_l.cooldown(users.Cooldown.MINING)
            minutes = (timedelta(minutes=6) - timediff) / timedelta(minutes=1)

            stats[8] += 1
            stats_changes = ':'.join([str(i) for i in stats])
            await update_footer(message, stats_changes)
            return await res.send_message("You are tired and cannot go mining "
                                          f"for another {minutes:0.1f} minutes.",
                                          ephemeral=True,
                                          delete_after=30)

        # Mining was successful, attempt to get some resources.
        stats[6] += 1

        # Update with a new mining attempt.
        user_l.mark_cooldown(users.Cooldown.MINING)

        material = Material(randint(Material.IRON, Material.VALORITE))
        vein_name = material.name.replace("_", ' ').lower()
        count = choice([0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 2, 2, 3])
        if count == 0:
            stats_changes = ':'.join([str(i) for i in stats])
            await update_footer(message, stats_changes)
            return await res.send_message(f"You struck a **{vein_name} vein** "
                                          "but fail to extract any ore.",
                                          ephemeral=True,
                                          delete_after=30)

        stats[7] += 1
        stats_changes = ':'.join([str(i) for i in stats])
        await update_footer(message, stats_changes)
        item = Item(Items.ORE,
                    material=material,
                    value=10,
                    uses=count,
                    uses_max=6)

        user_l.bank.add_item(item)
        user_l.bank.save()

        try:
            return await res.send_message(f"You struck a **{vein_name} vein** "
                                          f"and extracted **{count} ore**!",
                                          ephemeral=True,
                                          delete_after=30)
        except BaseException as exc:
            Log.player(f"{author} could not complete mining order, {exc}",
                       guild_id=guild.id, user_id=author.id)


async def setup(bot: discord.Client) -> None:
    """This is called by process that loads extensions."""
    bot.add_view(UserManagementView(bot))
    bot.add_view(ResourceView(bot))
