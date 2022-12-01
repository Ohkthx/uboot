import discord
from discord import ui, ButtonStyle

from dclient import DiscordBot
from dclient.modals import SupportModal


class GetSupportView(ui.View):
    def __init__(self, bot: DiscordBot) -> None:
        self.bot = bot
        super().__init__(timeout=None)

    embed = discord.Embed(title="Found a bug, stuck, or need help in "
                          "private?",
                          description="If you have found a bug or need "
                          "additional assistance that is not publicly "
                          "displayed, feel free to press the button based on "
                          "type of issue below and we will be right with you!",
                          color=discord.Color.green())

    @ui.button(label='✉ In-Game', style=ButtonStyle.green,
               custom_id='get_support_view:in_game')
    async def in_game_opt(self, interaction: discord.Interaction, button: ui.Button):
        modal = SupportModal(self.bot, "In_Game")
        await interaction.response.send_modal(modal)
        await modal.wait()

    @ui.button(label='✉ Discord', style=ButtonStyle.blurple,
               custom_id='get_support_view:discord')
    async def discord_opt(self, interaction: discord.Interaction, button: ui.Button):
        modal = SupportModal(self.bot, "Discord")
        await interaction.response.send_modal(modal)
        await modal.wait()

    @ui.button(label='✉ Website', style=ButtonStyle.red,
               custom_id='get_support_view:website')
    async def website_opt(self, interaction: discord.Interaction, button: ui.Button):
        modal = SupportModal(self.bot, "Website")
        await interaction.response.send_modal(modal)
        await modal.wait()

    @ui.button(label='✉ Other', style=ButtonStyle.grey,
               custom_id='get_support_view:other')
    async def other_opt(self, interaction: discord.Interaction, button: ui.Button):
        modal = SupportModal(self.bot, "Other")
        await interaction.response.send_modal(modal)
        await modal.wait()


async def setup(bot: DiscordBot) -> None:
    bot.add_view(GetSupportView(bot))
