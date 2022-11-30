import traceback
from datetime import datetime

import discord
from discord import ui

from managers import settings, tickets
from dclient import DiscordBot
from dclient.helper import get_channel
from dclient.views.threads import SupportThreadView


class SupportModal(ui.Modal, title='Support Request'):
    def __init__(self, bot: DiscordBot) -> None:
        self.bot = bot
        super().__init__()

    item = ui.TextInput(
        label='Category for request',
        placeholder='in-game, discord, website, or other',
    )

    description = ui.TextInput(
        label='Description for request',
        style=discord.TextStyle.long,
        placeholder='Type your description here...',
        required=True,
        max_length=300,
    )

    async def on_submit(self, interaction: discord.Interaction):
        res = interaction.response
        if not interaction.guild:
            return

        setting = settings.Manager.get(interaction.guild.id)
        channel = await get_channel(self.bot, setting.support_channel_id)
        if not channel:
            await res.send_message("Support channel may be unset.",
                                   ephemeral=True)
            return
        if not isinstance(channel, discord.TextChannel):
            await res.send_message("Support channel not set to a Text Channel.",
                                   ephemeral=True)
            return

        role = interaction.guild.get_role(setting.support_role_id)
        if not role:
            await res.send_message("Support role may be unset.",
                                   ephemeral=True)
            return

        user = interaction.user
        ticket_id = tickets.Manager.total() + 1
        title = f"ticket-{ticket_id}"
        thread = await channel.create_thread(name=title,
                                             type=discord.ChannelType.private_thread)
        embed = discord.Embed(title=f"New ticket opened!  id: {title}",
                              color=discord.Colour.brand_red(),
                              description=f"Created by: {user.mention}, id: {user.id}\n\n"
                              f"Type: **{self.item.value}**\n"
                              f"{self.description.value}\n\n"
                              "Please provide any additional relatable "
                              "information such as username, location, time, "
                              "what you were doing, etc. down below so that "
                              f"{role.mention} can assist you efficiently."
                              )
        ts = datetime.utcnow().replace(microsecond=0).isoformat()
        embed.set_footer(text=f"UTC Timestamp: {ts}Z")
        await thread.send(embed=embed,
                          content="Summoning assistance... Hail, "
                          f"{role.mention}!",
                          view=SupportThreadView(self.bot)
                          )
        await thread.add_user(interaction.user)
        await res.send_message('Ticket opened! Click the link to access: '
                               f'{thread.mention}', ephemeral=True)
        ticket = tickets.Manager.get(ticket_id)
        ticket.title = title
        self.bot._db.ticket.update(ticket)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        res = interaction.response
        await res.send_message('Oops! Something went wrong, please notify an '
                               'admin for additional help.', ephemeral=True)
        traceback.print_tb(error.__traceback__)
