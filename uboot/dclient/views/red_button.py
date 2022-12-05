import random
from itertools import repeat

import discord
from discord import ui

from dclient import DiscordBot
from managers import users


red_button_text = ["Nothing appears to have happened."]
red_button_text.extend(repeat("Nothing happened.", 6))


class RedButtonView(ui.View):
    def __init__(self, bot: DiscordBot) -> None:
        self.bot = bot
        super().__init__(timeout=None)

    @staticmethod
    def get_panel() -> discord.Embed:
        color = discord.Colour.from_str("#00ff08")
        return discord.Embed(description="A wild red button appeared!",
                             color=color)

    @ui.button(label='Do NOT Press', style=discord.ButtonStyle.red,
               custom_id='red_button_view:red')
    async def do_not(self, interaction: discord.Interaction, button: ui.Button):
        user = users.Manager.get(interaction.user.id)
        user.button_press += 1
        user.save()
        val = red_button_text[random.randrange(0, len(red_button_text))]
        await interaction.response.send_message(val, ephemeral=True)


async def setup(bot: DiscordBot) -> None:
    bot.add_view(RedButtonView(bot))
