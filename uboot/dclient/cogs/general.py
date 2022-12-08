from datetime import datetime

import discord
from discord.ext import commands
from discord.ext.commands import param

from dclient import DiscordBot


class General(commands.Cog):
    """General commands with no real category."""

    def __init__(self, bot: DiscordBot) -> None:
        self.bot = bot

    @commands.command(name='ping')
    async def ping(self, ctx: commands.Context) -> None:
        """PONG! Displays current latency between Discord and the bot."""
        now_ts = datetime.now().timestamp()
        latency = (now_ts - ctx.message.created_at.timestamp()) * 1000
        await ctx.send(f"Pong!  Latency: {abs(latency):0.2f} ms.")

    @commands.command(name="s2s")
    async def s2s(self, ctx: commands.Context) -> None:
        """Sucks to suck."""
        await ctx.message.delete()
        await ctx.send("Sucks to suck.")

    @commands.dm_only()
    @commands.command(name='remove', aliases=("rm",))
    async def rm(self, ctx: commands.Context,
                 limit: int = param(
                     description="Amount of messages to delete.")) -> None:
        """Removes 'n' amount of bot messages from DMs."""
        async for message in ctx.channel.history():
            if limit <= 0:
                return
            if message.author == self.bot.user:
                limit -= 1
                await message.delete()

    @commands.guild_only()
    @commands.is_owner()
    @commands.command()
    async def sync(self, ctx: commands.Context) -> None:
        """Syncs the current slash commands with the guild."""
        if not ctx.guild:
            return
        synced = await ctx.bot.tree.sync()
        await ctx.send(f"Synced {len(synced)} commands to the current guild.")


async def setup(bot: DiscordBot) -> None:
    await bot.add_cog(General(bot))
