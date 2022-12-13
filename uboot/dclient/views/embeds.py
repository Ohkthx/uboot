from typing import Optional

import discord
from discord import ui

from dclient.modals.edit_embed import EmbedModal

options = ['green', 'red', 'black', 'blue', 'yellow']


class EmbedView(ui.View):
    def __init__(self, user: int, message: Optional[discord.Message]) -> None:
        self.user = user
        self.message = message
        self.last_color: str = ''
        super().__init__(timeout=60)

    def current_color(self) -> Optional[discord.Colour]:
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
               custom_id='embed_view:menu',
               placeholder="Select embed color.")
    async def select_dropdown(self, interaction: discord.Interaction,
                              select: ui.Select):
        res = interaction.response
        if interaction.user.id != self.user:
            return await res.send_message("You did not initiate that command.",
                                          ephemeral=True,
                                          delete_after=30)

        self.last_color = select.values[0]
        await res.send_message(f"Embed color set to '{select.values[0]}'.",
                               ephemeral=True,
                               delete_after=30)

    @ui.button(label='Launch Creator', style=discord.ButtonStyle.green,
               custom_id='embed_view:create')
    async def create(self, interaction: discord.Interaction, button: ui.Button):
        res = interaction.response
        if interaction.user.id != self.user:
            return await res.send_message("You did not initiate that command.",
                                          ephemeral=True,
                                          delete_after=30)
        if interaction.message:
            await interaction.message.delete()

        modal = EmbedModal(color=self.current_color())
        await res.send_modal(modal)
        await modal.wait()

    @ui.button(label='Launch Editor', style=discord.ButtonStyle.red,
               custom_id='embed_view:edit')
    async def edit(self, interaction: discord.Interaction, button: ui.Button):
        res = interaction.response
        if interaction.user.id != self.user:
            return await res.send_message("You did not initiate that command.",
                                          ephemeral=True,
                                          delete_after=30)

        if interaction.message:
            await interaction.message.delete()

        if not self.message:
            return await res.send_message("You need to provide a valid "
                                          "message to edit",
                                          ephemeral=True,
                                          delete_after=30)
        if not EmbedModal.get_embed(self.message):
            return await res.send_message("That message does not have any embeds.",
                                          ephemeral=True,
                                          delete_after=30)

        modal = EmbedModal(color=self.current_color(), message=self.message)
        await res.send_modal(modal)
        await modal.wait()
