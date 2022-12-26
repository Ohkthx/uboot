"""Provides a generic reason form to forward information to a user."""
import traceback

import discord
from discord import ui


class DMResponseModal(ui.Modal, title='Reason'):
    """Adds a response to a DM."""

    def __init__(self, user: discord.User) -> None:
        self.to_user = user
        super().__init__()

    # Reason for action.
    response = ui.TextInput(
        label='Response',
        style=discord.TextStyle.long,
        placeholder='Type your response here...',
        required=True,
        max_length=2000,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Called when the submit button is pressed. Processes the
        interaction.
        """
        res = interaction.response
        await self.to_user.send(self.response.value)
        await res.send_message("message sent", delete_after=15)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        """Clean way of handling errors and notifying the user."""
        res = interaction.response
        await res.send_message('Oops! Something went wrong, please notify an '
                               'admin for additional help.',
                               ephemeral=True,
                               delete_after=60)
        traceback.print_tb(error.__traceback__)
