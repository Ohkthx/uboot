import discord
from discord import ui

from dclient import DiscordBot


class PersistentView(ui.View):
    def __init__(self, bot: DiscordBot) -> None:
        self.bot = bot
        super().__init__(timeout=None)

    @ui.button(label='Green', style=discord.ButtonStyle.green, custom_id='persistent_view:green')
    async def green(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message('This is green.', ephemeral=True)

    @ui.button(label='Red', style=discord.ButtonStyle.red, custom_id='persistent_view:red')
    async def red(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message('This is red.', ephemeral=True)

    @ui.button(label='Grey', style=discord.ButtonStyle.grey, custom_id='persistent_view:grey')
    async def grey(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message('This is grey.', ephemeral=True)


async def setup(bot: DiscordBot) -> None:
    bot.add_view(PersistentView(bot))
