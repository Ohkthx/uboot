from datetime import datetime
from multiprocessing import connection

from discord.ext import commands

from dclient import DiscordBot


class General(commands.Cog):
    def __init__(self, bot: DiscordBot) -> None:
        self._bot = bot

    @commands.command(name='ping')
    async def ping(self, ctx: commands.Context) -> None:
        now_ts = datetime.now().timestamp()
        latency = (now_ts - ctx.message.created_at.timestamp()) * 1000
        await ctx.send(f"Pong!  Latency: {abs(latency):0.2f} ms.")

    @commands.command(name='rm')
    async def rm(self, ctx: commands.Context, limit: int) -> None:
        channel = ctx.channel
        await channel.purge(limit=limit + 1)


async def setup(bot: DiscordBot) -> None:
    await bot.add_cog(General(bot))
