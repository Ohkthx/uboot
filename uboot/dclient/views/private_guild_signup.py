"""The panel and button combination used to request the creation of a new
guild. This request is forwarded to staff/admins to approve or deny.
"""
import discord
from discord import ui

from dclient import DiscordBot
from dclient.modals.guild_signup import GuildSignupModal


class GuildSignupView(ui.View):
    """Guild Signup View is used by users to create a new guild request."""

    def __init__(self, bot: DiscordBot) -> None:
        self.bot = bot
        super().__init__(timeout=None)

    @staticmethod
    def get_panel() -> discord.Embed:
        """Panel used to outline what the mechanic is."""
        title = "Interested in your own private guild?"
        desc = "Private Guilds are privatized threads that are strictly "\
            "invite only. Upon Creation, a promotional text is created "\
            "below that allows non-members to request access.\n\n"\
            "**Join others!**\n"\
            "> Select any Guild Promotion that feels like a home to you. By "\
            " pressing the 'Request to Join', the guild will notified of "\
            " your interests to join them.\n\n"\
            "**Establish your community!**\n"\
            "> If you wish to create your own community, begin by pressing the "\
            "'Create Guild Request' button below to fill out the form. An "\
            "admin will review your guilds application for approval.\n"\
            "> \n"\
            "> __**Required Information**__\n"\
            "> ├ Guild name [ex. Muffin Makers]\n"\
            "> ├ Abbreviation [ex. MM]\n"\
            "> └ Description for others to see.\n"\

        color = discord.Colour.from_str("#00ff08")
        return discord.Embed(title=title, description=desc, color=color)

    @ui.button(label='Create Guild Request', style=discord.ButtonStyle.blurple,
               custom_id='guild_signup_view:request')
    async def request(self, interaction: discord.Interaction, button: ui.Button):
        """Upon pressing the button, the user is prompted to supply information
        about their private guild. This information is sent to admin/staff to
        approve or deny the new guild request.
        """
        if not interaction.guild:
            return

        # The channel has to be inside a text channel so that threads can be
        # created.
        channel = interaction.channel
        if not channel or not isinstance(channel, discord.TextChannel):
            return

        # Create the modals and ask the user for guild information.
        modal = GuildSignupModal(self.bot, channel)
        res = interaction.response
        await res.send_modal(modal)
        await modal.wait()


async def setup(bot: DiscordBot) -> None:
    """This is called by process that loads extensions."""
    bot.add_view(GuildSignupView(bot))
