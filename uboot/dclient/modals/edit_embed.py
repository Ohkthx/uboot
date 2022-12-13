import traceback
from typing import Optional

import discord
from discord import ui

from managers import settings


class EmbedModal(ui.Modal, title='Embed Manager'):
    def __init__(self, color: Optional[discord.Colour] = None,
                 message: Optional[discord.Message] = None) -> None:
        self.color = color
        self.message = message
        super().__init__()

    embed_author = ui.TextInput(
        label='Author',
        style=discord.TextStyle.short,
        placeholder='Optional new author.',
        required=False,
        max_length=62,
    )

    embed_title = ui.TextInput(
        label='Title',
        style=discord.TextStyle.short,
        placeholder='Optional new title.',
        required=False,
        max_length=150,
    )

    embed_desc = ui.TextInput(
        label='Description',
        style=discord.TextStyle.long,
        placeholder='Optional new description.',
        required=False,
        max_length=300,
    )

    embed_footer = ui.TextInput(
        label='Footer',
        style=discord.TextStyle.short,
        placeholder='Optional new footer.',
        required=False,
        max_length=75,
    )

    @staticmethod
    def get_embed(message: discord.Message) -> Optional[discord.Embed]:
        if len(message.embeds) == 0:
            return None
        return message.embeds[0]

    async def on_submit(self, interaction: discord.Interaction) -> None:
        res = interaction.response
        user = interaction.user
        if not user:
            return

        embed = discord.Embed()
        if self.message:
            embed = EmbedModal.get_embed(self.message)
            if not embed:
                return await res.send_message("There is no embed attached "
                                              "to that message.",
                                              ephemeral=True,
                                              delete_after=60)

        value = self.embed_author.value
        if value:
            if value == "unset":
                value = ""
            embed.set_author(name=value)

        value = self.embed_title.value
        if value:
            if value == "unset":
                value = ""
            embed.title = value

        value = self.embed_desc.value
        if value:
            if value == "unset":
                value = ""
            embed.description = value

        value = self.embed_footer.value
        if value:
            if value == "unset":
                value = ""
            embed.set_footer(text=value)

        if self.color:
            embed.color = self.color

        if self.message:
            await self.message.edit(embed=embed)
        else:
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
