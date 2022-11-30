import discord
from discord import ui

from managers import tickets
from dclient import DiscordBot
from dclient.helper import thread_close


class SupportThreadView(ui.View):
    def __init__(self, bot: DiscordBot) -> None:
        self.bot = bot
        super().__init__(timeout=None)

    @ui.button(label='🔒 Close', style=discord.ButtonStyle.grey,
               custom_id='support_thread_view:close')
    async def support(self, interaction: discord.Interaction, button: ui.Button):
        channel = interaction.channel
        if not channel:
            return

        if not isinstance(channel, discord.Thread):
            return

        ticket = tickets.Manager.by_title(channel.name)
        if not ticket:
            ticket = tickets.Manager.get(tickets.Manager.total() + 1)
            ticket.title = channel.name

        ticket.done = True
        self.bot._db.ticket.update(ticket)

        res = interaction.response
        await res.send_message("Support thread closed by "
                               f"**{interaction.user}**.")

        user_msg = f"Your thread was closed by **{interaction.user}**."
        if interaction.user.id == channel.owner_id:
            user_msg = ""
        await thread_close("open", "closed", channel,
                           "unlisted closure", user_msg)


async def setup(bot: DiscordBot) -> None:
    bot.add_view(SupportThreadView(bot))
