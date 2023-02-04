"""Views / Panels used for testing new features or referencing."""
import discord
from discord import ui

from dclient.bot import DiscordBot


class Dropdown(ui.Select):
    """Simple dropdown menu for selecting options."""

    def __init__(self):
        options = [
            discord.SelectOption(
                label='Red', description='Your favourite colour is red', emoji='🟥'),
            discord.SelectOption(
                label='Green', description='Your favourite colour is green', emoji='🟩'),
            discord.SelectOption(
                label='Blue', description='Your favourite colour is blue', emoji='🟦'),
        ]
        super().__init__(options=options, custom_id="test_dropdown")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(f'Your favourite colour is {self.values[0]}')


# Possible options for a drop-down menu.
dropdown_opts = ['discord', 'in-game', 'website', 'other']


class PersistentView(ui.View):
    """Persistent View that can be interacted with after reboots."""

    def __init__(self, bot: DiscordBot) -> None:
        self.bot = bot
        super().__init__(timeout=None)

    # Last option selected from the dropdown menu.
    last_dropdown: str = ""

    @ui.select(options=[discord.SelectOption(label=item) for item in dropdown_opts],
               custom_id='persistent_view:menu',
               placeholder="Select one below.")
    async def select_dropdown(self, interaction: discord.Interaction,
                              select: Dropdown):
        """Prompts the user to select and option."""
        PersistentView.last_dropdown = select.values[0]
        res = interaction.response
        await res.send_message(f'You selected {select.values[0]}')

    @ui.button(label='Green', style=discord.ButtonStyle.green,
               custom_id='persistent_view:green')
    async def green(self, interaction: discord.Interaction, _: ui.Button):
        """Green button to interact with."""
        res = interaction.response
        await res.send_message('This is green, last: '
                               f'{PersistentView.last_dropdown}',
                               ephemeral=True)

    @ui.button(label='Red', style=discord.ButtonStyle.red,
               custom_id='persistent_view:red')
    async def red(self, interaction: discord.Interaction, _: ui.Button):
        """Red button to interact with."""
        res = interaction.response
        await res.send_message(f'This is red, last: {self.last_dropdown}',
                               ephemeral=True)

    @ui.button(label='Grey', style=discord.ButtonStyle.grey,
               custom_id='persistent_view:grey')
    async def grey(self, interaction: discord.Interaction, _: ui.Button):
        """Grey button to interact with."""
        res = interaction.response
        await res.send_message(f'This is grey, last: {self.last_dropdown}',
                               ephemeral=True)


async def setup(bot: DiscordBot) -> None:
    """This is called by process that loads extensions."""
    bot.add_view(PersistentView(bot))
