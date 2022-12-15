"""Embed Modal used for prompting user input in creating or editing embeds."""
import traceback
from typing import Optional

import discord
from discord import ui


class EmbedModal(ui.Modal, title='Embed Manager'):
    """Embed Modal used for prompting user input in creating or editing
    embeds.
    """

    def __init__(self, color: Optional[discord.Colour] = None,
                 message: Optional[discord.Message] = None) -> None:
        self.color = color
        self.message = message
        super().__init__()

    # For the Author portion of the Embed.
    embed_author = ui.TextInput(
        label='Author',
        style=discord.TextStyle.short,
        placeholder='Optional new author.',
        required=False,
        max_length=62,
    )

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
        max_length=300,
    )

    # For the Footer portion of the Embed.
    embed_footer = ui.TextInput(
        label='Footer',
        style=discord.TextStyle.short,
        placeholder='Optional new footer.',
        required=False,
        max_length=75,
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

        # Set the author.
        value = self.embed_author.value
        if value:
            if value == "unset":
                value = ""
            embed.set_author(name=value)

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

        # Set the color, if it was passed.
        if self.color:
            embed.color = self.color

        if self.message:
            # Upload the new embed if we're editing.
            await self.message.edit(embed=embed)
        else:
            # Resolve the channel and create the new embed.
            channel = interaction.channel
            if not channel or not isinstance(channel, discord.TextChannel):
                return await res.send_message("Could not find channel to "
                                              "send embed to.",
                                              ephemeral=True,
                                              delete_after=60)
            await channel.send(embed=embed)

        await res.send_message("Embed edited.", ephemeral=True, delete_after=60)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        res = interaction.response
        await res.send_message('Oops! Something went wrong, please notify an '
                               'admin for additional help.',
                               ephemeral=True,
                               delete_after=60)
        traceback.print_tb(error.__traceback__)
