from datetime import datetime

import discord
from discord.ext import commands
from discord.ext.commands import param

from managers import settings, subguilds
from dclient import DiscordBot
from dclient.helper import get_member, get_channel
from dclient.views.private_guild_signup import GuildSignupView


class Guild(commands.Cog):
    """Guilds are private threads existing in a large Discord server.
    Guilds are strictly invite only with the guild leader having
    basic abilities to manage it.

    Popular commands:
        (prefix)help guild
        (prefix)guild kick @UserToKick
    """

    def __init__(self, bot: DiscordBot) -> None:
        self.bot = bot

    @commands.guild_only()
    @commands.group(name="guild")
    async def guild(self, ctx: commands.Context) -> None:
        """Guilds are private threads existing in a large Discord server.
        Guilds are strictly invite only with the guild leader having
        basic abilities to manage it.

        Popular commands:
            (prefix)help guild
            (prefix)guild kick @UserToKick
        """
        if not ctx.invoked_subcommand:
            await ctx.send('invalid guild command.')

    @commands.is_owner()
    @commands.guild_only()
    @guild.command(name="panel")
    async def panel(self, ctx: commands.Context):
        """The 'Request / Signup' Panel for Guilds."""
        await ctx.send(embed=GuildSignupView.get_panel(),
                       view=GuildSignupView(self.bot))

    @commands.guild_only()
    @guild.command(name="kick")
    async def kick(self, ctx: commands.Context,
                   user: discord.Member = param(description="User to kick")):
        """Kicks the mentioned user from the guild.
        Only the guild leader can kick.
        Cannot kick guild leader or the bot.

        examples:
            (prefix)guild kick @BadApple
        """
        if not ctx.guild or not ctx.channel:
            return await ctx.send("Must be used in a guild channel.",
                                  delete_after=60)
        if not isinstance(ctx.channel, discord.Thread):
            return await ctx.send("Must be used in a guild thread.",
                                  delete_after=60)

        subguild = subguilds.Manager.by_thread(ctx.guild.id, ctx.channel.id)
        if not subguild or ctx.author.id != subguild.owner_id:
            return await ctx.send("Must be the owner of guild where the "
                                  "command is being used.",
                                  delete_after=60)

        if ctx.author == user:
            return await ctx.send("You cannot kick yourself.", delete_after=60)
        if self.bot.user and self.bot.user == user:
            return await ctx.send("You cannot kick the bot.", delete_after=60)

        await ctx.channel.remove_user(user)
        color = discord.Color.from_str("#F1C800")  # Yellow color.
        desc = f"**Removed**: {user.mention}\n"\
            f"**Date**: {datetime.utcnow().replace(microsecond=0)} UTC"
        embed = discord.Embed(title="User Kicked",
                              color=color,
                              description=desc)
        await ctx.channel.send(embed=embed)


async def setup(bot: DiscordBot) -> None:
    await bot.add_cog(Guild(bot))
