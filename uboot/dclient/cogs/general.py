from datetime import datetime

import discord
from discord.ext import commands
from discord.ext.commands import param

from dclient import DiscordBot


class General(commands.Cog):
    def __init__(self, bot: DiscordBot) -> None:
        self.bot = bot

    @commands.command(name='ping')
    async def ping(self, ctx: commands.Context) -> None:
        """PONG! Displays current latency between Discord and the bot."""
        now_ts = datetime.now().timestamp()
        latency = (now_ts - ctx.message.created_at.timestamp()) * 1000
        await ctx.send(f"Pong!  Latency: {abs(latency):0.2f} ms.")

    @commands.has_permissions(manage_messages=True)
    @commands.command(name='rm')
    async def rm(self, ctx: commands.Context,
                 limit: int = param(
                     description="Amount of messages to delete.")) -> None:
        """Removes 'n' amount of messages."""
        c = ctx.channel
        if isinstance(c, discord.Thread) or isinstance(c, discord.TextChannel):
            await c.purge(limit=limit + 1)

    @commands.dm_only()
    @commands.command(name='rm_dm')
    async def rm_dm(self, ctx: commands.Context, limit: int) -> None:
        """Removes 'n' amount of bot messages from DMs."""
        async for message in ctx.channel.history():
            if limit <= 0:
                return
            if message.author == self.bot.user:
                limit -= 1
                await message.delete()


async def setup(bot: DiscordBot) -> None:
    await bot.add_cog(General(bot))
