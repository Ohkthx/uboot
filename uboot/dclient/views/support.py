import discord
from discord import ui, ButtonStyle

from dclient import DiscordBot
from dclient.modals.support import SupportModal


class GetSupportView(ui.View):
    def __init__(self, bot: DiscordBot) -> None:
        self.bot = bot
        super().__init__(timeout=None)

    @staticmethod
    def get_panel() -> discord.Embed:
        title = "Found a bug or need help in private?"
        color = discord.Colour.from_str("#00ff08")
        desc = "If you would like to submit a support ticket, feel free to "\
            "select the type of support you are requesting by pressing the "\
            "related button below. You will be prompted to type a short "\
            "description for the ticket.\n\n"\
            "> __**Options**:__\n"\
            "> ├ **In-Game**: In-Game ticket.\n"\
            "> ├ **Discord**: Discord ticket.\n"\
            "> ├ **Website**: Website ticket.\n"\
            "> └ **Other**: Unknown/Other ticket.\n\n"\
            "__Note__: This will provide you a link to a private discord "\
            "channel only accessible by authorized staff."
        return discord.Embed(title=title, description=desc, color=color)

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
