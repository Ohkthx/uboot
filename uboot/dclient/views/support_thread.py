"""Support Thread View is the panel used by both the user and admins to control
the Support Ticket.
"""
from datetime import datetime
from typing import Union

import discord
from discord import ui

from managers import tickets, settings
from dclient.helper import thread_close, get_role, get_member
from dclient.modals.generic_reason import ReasonModal


class SupportThreadView(ui.View):
    """Support Thread View is the panel used by both the user and admins to
    control the Support Ticket.
    """

    def __init__(self, bot: discord.Client) -> None:
        self.bot = bot
        super().__init__(timeout=None)

    @staticmethod
    def get_panel(creator: Union[discord.User, discord.Member],
                  req_role: discord.Role,
                  name: str, issue_type: str,
                  description: str) -> discord.Embed:
        """Creates the panel, which is just an embed outlining some
        information
        """
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
            f"> └ **Close**: [{req_role.mention}] Lock thread, prompts reason.\n\n"\
            "__Note__: Please leave the thread when your ticket is complete. "\
            "When the thread is closed, you will be removed and a reason "\
            "will be provided."
        embed = discord.Embed(title=title, description=desc,
                              color=color, timestamp=datetime.utcnow())
        embed.set_footer(text="Ticket created at (UTC)")
        return embed

    @ui.button(label='↵ Leave', style=discord.ButtonStyle.blurple,
               custom_id='support_thread_view:leave')
    async def leave(self, interaction: discord.Interaction, button: ui.Button):
        """This is a button used by the user to leave the thread. Prevents them
        from getting future updates to the thread if admins/staff need to
        further discuss the issue.
        """
        guild = interaction.guild
        thread = interaction.channel
        if not guild or not thread:
            # Unknown how we got here, quit quietly.
            return

        # Ensure we are in a thread.
        if not isinstance(thread, discord.Thread):
            return

        # Remove the user who pressed the button.
        await thread.remove_user(interaction.user)

    @ui.button(label='🔒 Close', style=discord.ButtonStyle.grey,
               custom_id='support_thread_view:close')
    async def close(self, interaction: discord.Interaction, button: ui.Button):
        """Closes the thread, this button is only accessible to the
        staff/admins with the role designated for them. This cleans up the
        thread by removing all users and closing it. The thread can still be
        viewd in the archived threads for the support channel.
        """
        guild = interaction.guild
        thread = interaction.channel
        if not guild or not thread:
            # Unknown how we got here, quit quietly.
            return

        # Ensure we are in a thread.
        if not isinstance(thread, discord.Thread):
            return

        # Get the support role required to perform the close.
        role_id = settings.Manager.get(guild.id).support_role_id
        role = await get_role(self.bot, guild.id, role_id)
        if not role:
            return

        # Get the users Member account.
        user = await get_member(self.bot, guild.id, interaction.user.id)
        if not user:
            return

        # Validate they can press the button.
        if not role in user.roles:
            embed = discord.Embed(title="Invalid Permissions",
                                  description=f"You must have the {role.mention} "
                                  "role to do that.",
                                  color=discord.Color.red())
            return await interaction.response.send_message(embed=embed,
                                                           ephemeral=True,
                                                           delete_after=60)

        # Parse the ticket information from the thread name.
        ticket_info = thread.name.split('-')
        ticket = tickets.Manager.by_name(guild.id, thread.name)
        if not ticket:
            # Ticket not found, create a dummy ticket in its place.
            ticket_id = tickets.Manager.last_id(guild.id) + 1
            ticket_type = "unknown"
            if len(ticket_info) == 2:
                ticket_type = str(ticket_info[1])
                try:
                    ticket_id = int(ticket_info[0])
                except BaseException:
                    pass

            # Update the newly created tickets information.
            ticket = tickets.Manager.get(guild.id, ticket_id)
            ticket.title = ticket_type

        # Notify the user that their support thread was closed.
        owner = await get_member(self.bot, guild.id, ticket.owner_id)
        res = interaction.response
        reason = ReasonModal(owner, user,
                             "Support Thread Closed",
                             f"**Ticket**: {thread.name}",
                             discord.Color.light_grey())
        await res.send_modal(reason)
        if await reason.wait():
            return

        # Update the tickets status.
        ticket.done = True
        ticket.save()

        # Close and cleanup the thread.
        await thread_close(["open", "in-progress"], "closed", thread,
                           "unlisted closure")


async def setup(bot: discord.Client) -> None:
    """This is called by process that loads extensions."""
    bot.add_view(SupportThreadView(bot))
