import traceback
from datetime import datetime

import discord
from discord import ui

from managers import settings, tickets
from dclient import DiscordBot
from dclient.helper import get_channel
from dclient.views.threads import SupportThreadView


class SupportModal(ui.Modal, title='Support Request'):
    def __init__(self, bot: DiscordBot, issue: str) -> None:
        self.bot = bot
        self.issue = issue.lower()
        super().__init__()

    description = ui.TextInput(
        label='Description for request',
        style=discord.TextStyle.long,
        placeholder='Type your description here...',
        required=True,
        max_length=300,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        res = interaction.response
        if not interaction.guild:
            return

        setting = settings.Manager.get(interaction.guild.id)
        channel = await get_channel(self.bot, setting.support_channel_id)
        if not channel:
            return await res.send_message("Support channel may be unset.",
                                          ephemeral=True,
                                          delete_after=60)
        if not isinstance(channel, discord.TextChannel):
            return await res.send_message("Support channel not set to a Text Channel.",
                                          ephemeral=True,
                                          delete_after=60)

        role = interaction.guild.get_role(setting.support_role_id)
        if not role:
            return await res.send_message("Support role may be unset.",
                                          ephemeral=True,
                                          delete_after=60)

        user = interaction.user
        ticket_id = tickets.Manager.last_id(interaction.guild.id) + 1
        thread_name = f"{ticket_id}-{self.issue}"
        thread = await channel.create_thread(name=thread_name,
                                             type=discord.ChannelType.private_thread)
        panel_text = SupportThreadView.get_panel(user, role, thread_name,
                                                 self.issue,
                                                 self.description.value)
        await thread.send(embed=panel_text,
                          content="Summoning assistance... Hail, "
                          f"{role.mention}!",
                          view=SupportThreadView(self.bot)
                          )
        await thread.add_user(interaction.user)
        await res.send_message('Ticket opened! Click the link to access: '
                               f'{thread.mention}',
                               ephemeral=True,
                               delete_after=120)
        ticket = tickets.Manager.get(interaction.guild.id, ticket_id)
        ticket.title = self.issue
        ticket.save()

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        res = interaction.response
        await res.send_message('Oops! Something went wrong, please notify an '
                               'admin for additional help.',
                               ephemeral=True,
                               delete_after=60)
        traceback.print_tb(error.__traceback__)
