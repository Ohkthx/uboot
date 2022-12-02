from datetime import datetime
from typing import Union

import discord
from discord import ui

from managers import tickets, settings
from dclient import DiscordBot
from dclient.helper import thread_close, get_role, get_member


class SupportThreadView(ui.View):
    def __init__(self, bot: DiscordBot) -> None:
        self.bot = bot
        super().__init__(timeout=None)

    @staticmethod
    def get_panel(creator: Union[discord.User, discord.Member],
                  req_role: discord.Role,
                  name: str, issue_type: str,
                  description: str) -> discord.Embed:
        title = "New ticket opened!"
        color = discord.Colour.from_str("#00ff08")
        fix_description = description.replace('\n', '\n> ')
        desc = f"**Created by**: `{creator}`\n"\
            f"**user id**: `{creator.id}`\n"\
            f"**ticket id**: `{name}`\n\n"\
            f"> **Type**: `{issue_type.replace('_', '-')}`\n"\
            f"> ```{fix_description}```\n\n"\
            "Please provide any additional relatable "\
            "information such as username, location, time, "\
            "what you were doing, etc. down below so that "\
            f"{req_role.mention} can assist you efficiently.\n\n"\
            "> __**Options**:__\n"\
            f"> ├ **Leave**: [{creator.mention}] Leave thread.\n"\
            f"> └ **Close**: [{req_role.mention}] Lock thread.\n\n"\
            "__Note__: Please leave the thread when your ticket is complete. "\
            "When the thread is closed, you will be removed."
        embed = discord.Embed(title=title, description=desc,
                              color=color, timestamp=datetime.utcnow())
        embed.set_footer(text=f"Ticket created at")

        return embed

    @ui.button(label='↵ Leave', style=discord.ButtonStyle.blurple,
               custom_id='support_thread_view:leave')
    async def leave(self, interaction: discord.Interaction, button: ui.Button):
        guild = interaction.guild
        thread = interaction.channel
        if not guild or not thread:
            return

        if not isinstance(thread, discord.Thread):
            return

        await thread.remove_user(interaction.user)

    @ui.button(label='🔒 Close', style=discord.ButtonStyle.grey,
               custom_id='support_thread_view:close')
    async def support(self, interaction: discord.Interaction, button: ui.Button):
        guild = interaction.guild
        thread = interaction.channel
        if not guild or not thread:
            return

        if not isinstance(thread, discord.Thread):
            return

        # Check role for button press.
        role_id = settings.Manager.get(guild.id).support_role_id
        role = await get_role(self.bot, guild.id, role_id)
        if not role:
            return

        user = await get_member(self.bot, guild.id, interaction.user.id)
        if not user:
            return

        if not role in user.roles:
            embed = discord.Embed(title="Invalid Permissions",
                                  description=f"You must have the {role.mention} "
                                  "role to do that.",
                                  color=discord.Color.red())
            return await interaction.response.send_message(embed=embed,
                                                           ephemeral=True)

        ticket_info = thread.name.split('-')
        ticket = tickets.Manager.by_name(guild.id, thread.name)
        if not ticket:
            ticket_id = tickets.Manager.total(guild.id) + 1
            ticket_type = "unknown"
            if len(ticket_info) == 2:
                ticket_type = str(ticket_info[1])
                try:
                    ticket_id = int(ticket_info[0])
                except BaseException:
                    pass

            ticket = tickets.Manager.get(guild.id, ticket_id)
            ticket.title = ticket_type

        ticket.done = True
        self.bot._db.ticket.update(ticket)

        user_msg = f"Support thread was closed by **{user}**."
        embed = discord.Embed(title="Thread Closed",
                              description=user_msg,
                              color=discord.Color.light_grey())
        await interaction.response.send_message(embed=embed)

        await thread_close(["open", "in-progress"], "closed", thread,
                           "unlisted closure")


async def setup(bot: DiscordBot) -> None:
    bot.add_view(SupportThreadView(bot))
