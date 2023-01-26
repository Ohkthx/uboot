"""User based views."""
from datetime import datetime, timedelta

import discord
from discord import ui

from dclient import DiscordBot
from dclient.helper import get_user, check_minigame
from dclient.destructable import Destructable, DestructableManager
from dclient.views.user import BankView, LocationView, UserView
from managers import users, entities
from managers.logs import Log


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


class UserActionView(ui.View):
    """Basic user actions for managing their character."""

    def __init__(self, bot: discord.Client) -> None:
        self.bot = bot
        super().__init__(timeout=None)

    @staticmethod
    def get_panel() -> discord.Embed:
        """Creates the panels embed for the basic action view."""
        embed = discord.Embed()
        embed.color = discord.Colour.from_str("#00ff08")
        embed.description = "Manage your user account below.\n\n"\
            f"__**Options**__:\n"\
            f"> ├ **Stats**, check your player status.\n"\
            f"> ├ **Bank**, manage your bank and sell items.\n"\
            f"> └ **Recall**, travel to a new location.\n"
        embed.set_footer(text="0:0:0:0:0")

        return embed

    @ui.button(label='Stats', style=discord.ButtonStyle.blurple,
               custom_id='user_action_view:stats')
    async def stats(self, interaction: discord.Interaction, button: ui.Button):
        """Displays the players stats."""
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
        passed, msg = await check_minigame(self.bot, user, guild.id)
        if not passed:
            return await res.send_message(msg, ephemeral=True, delete_after=30)

        # Remove the old views.
        category = Destructable.Category.OTHER
        await DestructableManager.remove_many(user.id, True, category)

        stats = extract_ints(message)
        stats[0] += 1
        stats_changes = ':'.join([str(i) for i in stats])
        await update_footer(message, stats_changes)

        # Create the stats view.
        view = UserView(self.bot)
        view.set_user(user)
        embed = UserView.get_panel(user)
        await res.send_message(embed=embed, view=view, ephemeral=True,
                               delete_after=60)

    @ui.button(label='Bank', style=discord.ButtonStyle.green,
               custom_id='user_action_view:bank')
    async def bank(self, interaction: discord.Interaction, button: ui.Button):
        """Displays the players bank."""
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
        passed, msg = await check_minigame(self.bot, user, guild.id)
        if not passed:
            return await res.send_message(msg, ephemeral=True, delete_after=30)

        # Remove the old views.
        category = Destructable.Category.OTHER
        await DestructableManager.remove_many(user.id, True, category)

        stats = extract_ints(message)
        stats[1] += 1
        stats_changes = ':'.join([str(i) for i in stats])
        await update_footer(message, stats_changes)

        view = BankView(self.bot)
        view.set_user(user)

        embed = BankView.get_panel(user)
        await res.send_message(embed=embed, view=view, ephemeral=True,
                               delete_after=60)

    @ui.button(label='Recall', style=discord.ButtonStyle.gray,
               custom_id='user_action_view:recall')
    async def Recall(self, interaction: discord.Interaction, button: ui.Button):
        """Displays the players location and recall areas."""
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
        passed, msg = await check_minigame(self.bot, user, guild.id)
        if not passed:
            return await res.send_message(msg, ephemeral=True, delete_after=30)

        # Remove the old views.
        category = Destructable.Category.OTHER
        await DestructableManager.remove_many(user.id, True, category)

        stats = extract_ints(message)
        stats[2] += 1
        stats_changes = ':'.join([str(i) for i in stats])
        await update_footer(message, stats_changes)

        view = LocationView(self.bot)
        view.set_user(user)

        embed = LocationView.get_panel(user)
        await res.send_message(embed=embed, view=view, ephemeral=True,
                               delete_after=60)


class TauntView(ui.View):
    """Creates a new taunt panel."""

    def __init__(self, bot: discord.Client) -> None:
        self.bot = bot
        super().__init__(timeout=None)

    @staticmethod
    def get_panel() -> discord.Embed:
        """Creates the panels embed for the taunt view."""
        embed = discord.Embed(title="Give a shout!")
        embed.color = discord.Colour.from_str("#00ff08")
        embed.description = "Interested in adventure?\nAre you brave?\n"\
            f"Trying to farm for new weapons, armor, or other items?\n"\
            f"Flex your skills and taunt nearby enemies.\n\n"\
            f"__**Options**__:\n"\
            f"> └ **TAUNT**, attempt to attract nearby enemies.\n\n"\
            "**Note**: This can place you into combat."
        embed.set_footer(text="0:0")

        return embed

    @ui.button(label='TAUNT', style=discord.ButtonStyle.red,
               custom_id='taunt_view:taunt')
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

        # Prevent taunt spam.
        user_l = users.Manager.get(author.id)
        if datetime.now() - user_l.last_taunt < timedelta(minutes=12):
            timediff = datetime.now() - user_l.last_taunt
            minutes = (timedelta(minutes=12) - timediff) / timedelta(minutes=1)
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

        stats = extract_ints(message)
        stats[0] += 1

        # Update with a new taunt attempt.
        user_l.last_taunt = datetime.now()

        # Spawn the creature.
        loc = user_l.c_location
        difficulty = user_l.difficulty
        inpowerhour = self.bot.powerhours.get(guild.id)
        entity = entities.Manager.check_spawn(loc, difficulty,
                                              inpowerhour is not None,
                                              user_l.powerhour is not None,
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


async def setup(bot: discord.Client) -> None:
    """This is called by process that loads extensions."""
    bot.add_view(UserActionView(bot))
    bot.add_view(TauntView(bot))
