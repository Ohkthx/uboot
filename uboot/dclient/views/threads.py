from datetime import datetime

import discord
from discord import ui

from managers import tickets
from dclient import DiscordBot
from dclient.helper import thread_close


class SupportThreadView(ui.View):
    def __init__(self, bot: DiscordBot) -> None:
        self.bot = bot
        super().__init__(timeout=None)

    @staticmethod
    def get_panel(creator: discord.User, req_role: discord.Role,
                  name: str, issue_type: str,
                  description: str) -> discord.Embed:
        title = f"New ticket opened!"
        color = discord.Colour.from_str("#00ff08")
        desc = f"**Created by**: `{creator}`\n"\
            f"**user id**: `{creator.id}`\n"\
            f"**ticket id**: `{name}`\n\n"\
            f"> **Type**: `{issue_type.replace('_', '-')}`\n"\
            f"> ```{description}```"\
            "\n\nPlease provide any additional relatable "\
            "information such as username, location, time, "\
            "what you were doing, etc. down below so that "\
            f"{req_role.mention} can assist you efficiently.\n\n"\
            "Note: Please do not close the ticket until all"\
            " members have had a chance to acknowledge "\
            "completion."
        embed = discord.Embed(title=title, description=desc,
                              color=color, timestamp=datetime.utcnow())
        embed.set_footer(text=f"Ticket created at")

        return embed

    @ui.button(label='🔒 Close', style=discord.ButtonStyle.grey,
               custom_id='support_thread_view:close')
    async def support(self, interaction: discord.Interaction, button: ui.Button):
        guild = interaction.guild
        channel = interaction.channel
        if not guild or not channel:
            return

        if not isinstance(channel, discord.Thread):
            return

        ticket_info = channel.name.split('-')
        ticket = tickets.Manager.by_name(guild.id, channel.name)
        if not ticket:
            ticket_id = tickets.Manager.total(guild.id) + 1
            ticket_type = "unknown"
            if len(ticket_info) == 2:
                ticket_type = str(ticket_info[1])
                try:
                    ticket_id = int(ticket_info[0])
                except:
                    pass

            ticket = tickets.Manager.get(guild.id, ticket_id)
            ticket.title = ticket_type

        ticket.done = True
        self.bot._db.ticket.update(ticket)

        res = interaction.response
        await res.send_message("Support thread closed by "
                               f"**{interaction.user}**.")

        user_msg = f"Your thread was closed by **{interaction.user}**."
        if interaction.user.id == channel.owner_id:
            user_msg = ""
        await thread_close(["open", "in-progress"], "closed", channel,
                           "unlisted closure", user_msg)


async def setup(bot: DiscordBot) -> None:
    bot.add_view(SupportThreadView(bot))
