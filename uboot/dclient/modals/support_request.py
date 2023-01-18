"""Support Request Modal is the form filled out by a user to get additional
assistance from staff.
"""
import traceback

import discord
from discord import ui

from managers import settings, tickets
from dclient.helper import get_channel
from dclient.views.support_thread import SupportThreadView


class SupportRequestModal(ui.Modal, title='Support Request'):
    """Support Request Form filled out by a user to get additional
    support from staff/admins. This is part of the Support Ticket system.
    """

    def __init__(self, issue: str) -> None:
        self.issue = issue.lower()
        super().__init__()

    # Description of the issue.
    description = ui.TextInput(
        label='Description for request',
        style=discord.TextStyle.long,
        placeholder='Type your description here...',
        required=True,
        max_length=300,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """This is called when the submit button is pressed. Processes
        the form by creating the support thread and bringing in all users.
        """
        res = interaction.response
        client = interaction.client
        guild = interaction.guild
        if not guild:
            return

        setting = settings.Manager.get(guild.id)

        # Make sure the support channel exists.
        channel = await get_channel(client, setting.support.channel_id)
        if not channel:
            return await res.send_message("Support channel may be unset.",
                                          ephemeral=True,
                                          delete_after=60)

        # Validate it is a text channel and can create threads.
        if not isinstance(channel, discord.TextChannel):
            return await res.send_message("Support channel not set to a Text Channel.",
                                          ephemeral=True,
                                          delete_after=60)

        # Get the role that will have access to give assistance.
        role = guild.get_role(setting.support.role_id)
        if not role:
            return await res.send_message("Support role may be unset.",
                                          ephemeral=True,
                                          delete_after=60)

        # Create the support ticket and thread.
        user = interaction.user
        ticket_id = tickets.Manager.last_id(guild.id) + 1
        thread_name = f"{ticket_id}-{self.issue}"
        thread = await channel.create_thread(name=thread_name,
                                             type=discord.ChannelType.private_thread)

        panel_text = SupportThreadView.get_panel(user, role, thread_name,
                                                 self.issue,
                                                 self.description.value)

        # Send the thread panel that admins will use to close the issue.
        await thread.send(embed=panel_text,
                          content="Summoning assistance... Hail, "
                          f"{role.mention}!",
                          view=SupportThreadView(client)
                          )

        # Add the user requesting help.
        await thread.add_user(interaction.user)
        await res.send_message('Ticket opened! Click the link to access: '
                               f'{thread.mention}',
                               ephemeral=True,
                               delete_after=120)

        # Update the ticket and save it.
        ticket = tickets.Manager.get(guild.id, ticket_id)
        ticket.title = self.issue
        ticket.owner_id = interaction.user.id
        ticket.save()

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        """Cleanly handles unknown errors with a pretty print out to the
        user.
        """
        res = interaction.response
        await res.send_message('Oops! Something went wrong, please notify an '
                               'admin for additional help.',
                               ephemeral=True,
                               delete_after=60)
        traceback.print_tb(error.__traceback__)
