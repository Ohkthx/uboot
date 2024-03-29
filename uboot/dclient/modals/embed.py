"""Embed Modal used for prompting user input in creating or editing embeds."""
import traceback
from typing import Optional, Union
from typing_extensions import TypeAlias

import discord
from discord import ui

from dclient.views.dm import DMDeleteView

Messagable: TypeAlias = Union[discord.Thread, discord.TextChannel]


class EmbedModal(ui.Modal, title='Embed Manager'):
    """Embed Modal used for prompting user input in creating or editing
    embeds.
    """

    def __init__(self, channel: Messagable,
                 color: Optional[discord.Colour] = None,
                 message: Optional[discord.Message] = None) -> None:
        self.channel = channel
        self.color = color
        self.message = message
        super().__init__()

    # For the Title portion of the Embed.
    embed_title = ui.TextInput(
        label='Title',
        style=discord.TextStyle.short,
        placeholder='Optional new title.',
        required=False,
        max_length=150,
    )

    # For the Description portion of the Embed.
    embed_desc = ui.TextInput(
        label='Description',
        style=discord.TextStyle.long,
        placeholder='Optional new description.',
        required=False,
        max_length=3000,
    )

    # For the Footer portion of the Embed.
    embed_footer = ui.TextInput(
        label='Footer',
        style=discord.TextStyle.short,
        placeholder='Optional new footer.',
        required=False,
        max_length=75,
    )

    # For the thumbnail portion of the Embed.
    embed_thumbnail_url = ui.TextInput(
        label='Thumbnail URL',
        style=discord.TextStyle.short,
        placeholder='Optional new thumbnail.',
        required=False,
        max_length=300,
    )

    # For the image portion of the Embed.
    embed_image_url = ui.TextInput(
        label='Image URL',
        style=discord.TextStyle.short,
        placeholder='Optional new image.',
        required=False,
        max_length=300,
    )

    @staticmethod
    def get_embed(message: discord.Message) -> Optional[discord.Embed]:
        """Attempts to extract the embed from the message if it exists."""
        if len(message.embeds) == 0:
            return None
        return message.embeds[0]

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Triggered when the 'Submit' button is pressed."""
        res = interaction.response
        user = interaction.user
        if not user:
            return

        embed = discord.Embed()
        if self.message:
            # If a message was passed, assume we are editing the embed.
            embed = EmbedModal.get_embed(self.message)
            if not embed:
                # Could not get the assumed messages embed, just return.
                return await res.send_message("There is no embed attached "
                                              "to that message.",
                                              ephemeral=True,
                                              delete_after=60)

        # Set the title.
        value = self.embed_title.value
        if value:
            if value == "unset":
                value = ""
            embed.title = value

        # Set the description.
        value = self.embed_desc.value
        if value:
            if value == "unset":
                value = ""
            embed.description = value

        # Set the footer.
        value = self.embed_footer.value
        if value:
            if value == "unset":
                value = ""
            embed.set_footer(text=value)

        # Set the thumbnail.
        value = self.embed_thumbnail_url.value
        if value:
            if value == "unset":
                value = ""
            embed.set_thumbnail(url=value)

        # Set the image.
        value = self.embed_image_url.value
        if value:
            if value == "unset":
                value = ""
            embed.set_image(url=value)

        # Set the color, if it was passed.
        if self.color:
            embed.colour = self.color

        status: str = "created"
        if self.message:
            # Upload the new embed if we're editing.
            status = "edited"
            self.message = await self.message.edit(embed=embed)
        else:
            self.message = await self.channel.send(embed=embed)

        url: str = ""
        if self.message:
            url = f"Go to message: [**Click Here**]({self.message.jump_url})"
        embed = discord.Embed(title=f"Embed {status}", description=url)
        embed.colour = discord.Color.blurple()
        view = DMDeleteView(interaction.client)
        await res.send_message(embed=embed, view=view, delete_after=60)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        res = interaction.response
        await res.send_message('Oops! Something went wrong, please notify an '
                               'admin for additional help.',
                               ephemeral=True,
                               delete_after=60)
        traceback.print_tb(error.__traceback__)
