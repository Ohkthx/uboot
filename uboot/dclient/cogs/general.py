from datetime import datetime
from typing import Optional

import discord
from discord.ext import commands
from discord.ext.commands import param

from dclient import DiscordBot
from dclient.views.embeds import EmbedView


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

    @commands.guild_only()
    @commands.is_owner()
    @commands.command()
    async def sync(self, ctx: commands.Context) -> None:
        """Syncs the current slash commands with the guild."""
        if not ctx.guild:
            return
        synced = await ctx.bot.tree.sync()
        await ctx.send(f"Synced {len(synced)} commands to the current guild.")

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
    @commands.has_permissions(manage_channels=True)
    @commands.command(name='embed')
    async def embed(self, ctx: commands.Context,
                    msg_id: int = param(description="id of the msg.",
                                        default=0),
                    ) -> None:
        """Either creates an embed or edits an embed authored by the bot.
        example:
            Create:  (prefix)embed
            Edit:    (prefix)embed 012345679
        """
        channel = ctx.channel
        guild = ctx.guild
        if not channel or not guild:
            return

        msg: Optional[discord.Message] = None
        if msg_id > 0:
            msg = await channel.fetch_message(msg_id)
            if not msg:
                await ctx.send("Could not find message by that id.",
                               delete_after=30)
                return

            if self.bot.user and msg.author.id != self.bot.user.id:
                await ctx.send("Can only attach to the bots messages.",
                               delete_after=30)
                return

        view = EmbedView(ctx.author.id, msg)
        await ctx.send(view=view, delete_after=30)
        if ctx.message:
            await ctx.message.delete()


async def setup(bot: DiscordBot) -> None:
    await bot.add_cog(General(bot))
