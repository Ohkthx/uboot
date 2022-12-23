"""Embed View is used to create and manage embeds created by the bot."""
from typing import Optional, Union

import discord
from discord import ui

from dclient.modals.embed import EmbedModal, Messageable

# All possible embed color options supported in the dropdown.
options = ['green', 'red', 'black', 'blue', 'yellow']

Messageable = Union[discord.Thread, discord.TextChannel]


class EmbedView(ui.View):
    """Embed View is used to create and manage embeds created by the bot."""

    def __init__(self, user: int, channel: Messageable, message: Optional[discord.Message]) -> None:
        self.user = user
        self.channel = channel
        self.message = message
        self.last_color: str = ''
        super().__init__(timeout=60)

    @staticmethod
    def get_panel() -> discord.Embed:
        """Creates the panel that is sent to the user."""
        embed = discord.Embed(title="Embed Creator / Editor")
        embed.color = discord.Color.blurple()
        embed.description = "If you wish to set or change the color of the "\
            "embed:\nSelect a color from the drop down menu before pressing "\
            "a button.\n\nThis menu disappears after 1 minute."
        return embed

    def current_color(self) -> Optional[discord.Colour]:
        """Extracts the currently selected color if there is one."""
        if self.last_color == 'red':
            return discord.Colour.from_str("#ff0f08")
        if self.last_color == 'yellow':
            return discord.Colour.from_str("#F1C800")
        if self.last_color == 'green':
            return discord.Colour.from_str("#00ff08")
        if self.last_color == 'blue':
            return discord.Colour.blue()
        if self.last_color == 'black':
            return discord.Colour.default()
        return None

    @ui.select(options=[discord.SelectOption(label=item) for item in options],
               custom_id='embed_view:dropdown_menu',
               placeholder="Select embed color.")
    async def select_dropdown(self, interaction: discord.Interaction,
                              select: ui.Select):
        """Represents the embeds dropdown menu for selecting a color."""
        res = interaction.response
        if interaction.user.id != self.user:
            return await res.send_message("You did not initiate that command.",
                                          ephemeral=True,
                                          delete_after=30)

        # Assign the color.
        self.last_color = select.values[0]
        await res.send_message(f"Embed color set to '{select.values[0]}'.",
                               ephemeral=True,
                               delete_after=30)

    @ui.button(label='Launch Creator', style=discord.ButtonStyle.green,
               custom_id='embed_view:create')
    async def create(self, interaction: discord.Interaction, button: ui.Button):
        """Create a new embed instead of editing one. The color selected in the
        dropdown menu will be the color of the newly created embed. Defaults
        to be just black.
        """
        res = interaction.response
        if interaction.user.id != self.user:
            return await res.send_message("You did not initiate that command.",
                                          ephemeral=True,
                                          delete_after=30)

        # Delete the message that spawn the button.
        if interaction.message:
            await interaction.message.delete()

        # Send the embed creation modal to the user.
        modal = EmbedModal(self.channel, color=self.current_color())
        await res.send_modal(modal)
        await modal.wait()

    @ui.button(label='Launch Editor', style=discord.ButtonStyle.red,
               custom_id='embed_view:edit')
    async def edit(self, interaction: discord.Interaction, button: ui.Button):
        """Edits a previously existing embed. This requires the message id of
        the embed to be passed so that it can be edited. The currently selected
        dropdown color will be the new color of the embed.
        """
        res = interaction.response
        if interaction.user.id != self.user:
            return await res.send_message("You did not initiate that command.",
                                          ephemeral=True,
                                          delete_after=30)

        # Only continue if a message was passed.
        if not self.message:
            return await res.send_message("You need to provide a valid "
                                          "message to edit",
                                          ephemeral=True,
                                          delete_after=30)

        # Delete the message that spawn the button.
        if interaction.message:
            await interaction.message.delete()

        # Verify that the message has an embed already.
        if not EmbedModal.get_embed(self.message):
            return await res.send_message("That message does not have any embeds.",
                                          ephemeral=True,
                                          delete_after=30)

        # Send the embed creation modal to the user (also allows editing.)
        modal = EmbedModal(self.channel,
                           color=self.current_color(),
                           message=self.message)
        await res.send_modal(modal)
        await modal.wait()
