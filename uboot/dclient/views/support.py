import discord
from discord import ui

from dclient import DiscordBot
from dclient.modals import SupportModal


class SupportView(ui.View):
    def __init__(self, bot: DiscordBot) -> None:
        self.bot = bot
        super().__init__(timeout=None)

    @ui.button(label='✉ Create Ticket', style=discord.ButtonStyle.green,
               custom_id='support_view:support')
    async def support(self, interaction: discord.Interaction, button: ui.Button):
        modal = SupportModal(self.bot)
        await interaction.response.send_modal(modal)
        await modal.wait()


async def setup(bot: DiscordBot) -> None:
    bot.add_view(SupportView(bot))
