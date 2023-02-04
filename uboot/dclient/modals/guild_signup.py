"""Guild Signup Modal used for registering a new guild."""
import traceback

import discord
from discord import ui

from managers import settings, subguilds
from dclient.bot import DiscordBot
from dclient.helper import get_channel
from dclient.views.private_guild_panel import GuildApprovalView


class GuildSignupModal(ui.Modal, title='Guild Request'):
    """Prompts the user with a form used to register a new guild. This data
    is passed to an admins channel to accept or decline the application.
    """

    def __init__(self, bot: DiscordBot, channel: discord.TextChannel) -> None:
        self.bot = bot
        self.channel = channel
        super().__init__()

    # Name of the guild.
    guild_name = ui.TextInput(
        label='Guild name',
        style=discord.TextStyle.short,
        placeholder='ex. Muffin Makers',
        required=True,
    )

    # Abbreviation of the guild.
    guild_abbrev = ui.TextInput(
        label='Guild abbreviation',
        style=discord.TextStyle.short,
        placeholder='ex. MM',
        required=True,
    )

    # Short promotional description.
    description = ui.TextInput(
        label='Description for guild',
        style=discord.TextStyle.long,
        placeholder='Type your description here...',
        required=True,
        max_length=300,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Called when the submit button is pressed."""
        res = interaction.response
        if not interaction.guild:
            return

        # Validate the settings.
        setting = settings.Manager.get(interaction.guild.id)
        channel = await get_channel(self.bot, setting.subguild.review_channel_id)
        if not channel:
            return await res.send_message("Request Review channel may be unset.",
                                          ephemeral=True,
                                          delete_after=60)
        if not isinstance(channel, discord.TextChannel):
            return await res.send_message("Review channel not set to a Text Channel.",
                                          ephemeral=True,
                                          delete_after=60)

        # Create the guilds default settings and save it.
        subguild_id = subguilds.Manager.last_id(interaction.guild.id) + 1
        subguild = subguilds.Manager.get(interaction.guild.id, subguild_id)
        subguild.name = self.guild_name.value
        subguild.owner_id = interaction.user.id
        subguild.save()

        # Create and send the Reviewers embed.
        embed = GuildApprovalView.get_panel(self.guild_name.value,
                                            self.guild_abbrev.value,
                                            self.description.value,
                                            interaction.user,
                                            subguild_id)
        await channel.send(embed=embed,
                           view=GuildApprovalView(self.bot))

        # Create and send the Users embed.
        color = discord.Colour.from_str("#00ff08")  # Green color.
        desc = f"**Guild Name**: {self.guild_name}\n"\
            f"**Description**:\n```{self.description}```\n\n"\
            "Your request is currently being reviewed."
        embed = discord.Embed(title="Request Submitted",
                              description=desc,
                              color=color)
        await res.send_message(embed=embed, ephemeral=True, delete_after=300)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        """Called if an unknown error occurs... just a pretty way of handling
        things.
        """
        res = interaction.response
        await res.send_message('Oops! Something went wrong, please notify an '
                               'admin for additional help.',
                               ephemeral=True,
                               delete_after=60)
        traceback.print_tb(error.__traceback__)
