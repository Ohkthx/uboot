"""Presents all users with a tempting red button to press. This button has a
temporary lifespan.
"""
import random
from itertools import repeat

import discord
from discord import ui

from dclient import DiscordBot
from managers import users, monsters


# Random texted presented to the user.
red_button_text = ["Nothing appears to have happened."]
red_button_text.extend(repeat("Nothing happened.", 6))


class RedButtonView(ui.View):
    """Fun and tempting button for users to NOT press."""

    def __init__(self, bot: DiscordBot) -> None:
        self.bot = bot
        super().__init__(timeout=None)

    @staticmethod
    def get_panel() -> discord.Embed:
        """Creates the panel for the button."""
        color = discord.Colour.from_str("#00ff08")
        return discord.Embed(description="A wild red button appeared!",
                             color=color)

    @ui.button(label='Do NOT Press', style=discord.ButtonStyle.red,
               custom_id='red_button_view:red')
    async def do_not(self, interaction: discord.Interaction, button: ui.Button):
        """The button the users must refrain from pressing."""
        res = interaction.response
        user = interaction.user
        if not interaction.message or not isinstance(user, discord.Member):
            return

        # Update the user who pressed it.
        user_l = users.Manager.get(user.id)
        user_l.button_press += 1
        user_l.save()

        rand = random.randrange(0, 200)
        if 0 <= rand < 5:
            # Spawn a monster.
            monster = monsters.Manager.spawn(user_l.difficulty())
            await self.bot.add_monster(interaction.message, user, monster)
            return

        # Set the button to be destroyed by the bot.
        val = red_button_text[random.randrange(0, len(red_button_text))]
        await res.send_message(val, ephemeral=True, delete_after=5)


async def setup(bot: DiscordBot) -> None:
    """This is called by process that loads extensions."""
    bot.add_view(RedButtonView(bot))
