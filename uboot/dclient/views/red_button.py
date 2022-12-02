import discord
from discord import ui


class RedButtonView(ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @staticmethod
    def get_panel() -> discord.Embed:
        color = discord.Colour.from_str("#00ff08")
        return discord.Embed(description="A red button spawned!", color=color)

    @ui.button(label='Do NOT Click', style=discord.ButtonStyle.red,
               custom_id='red_button_view:red')
    async def do_not(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("Nothing happened.",
                                                ephemeral=True)
