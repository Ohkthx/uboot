import discord
from discord.ext import commands

from dclient import DiscordBot
from dclient.views.test import PersistentView


class Test(commands.Cog):
    """For testing new ideas."""

    def __init__(self, bot: DiscordBot) -> None:
        self.bot = bot

    @commands.is_owner()
    @commands.guild_only()
    @commands.group(name="test")
    async def test(self, ctx: commands.Context) -> None:
        if not ctx.invoked_subcommand:
            await ctx.send('invalid button-test command.')

    @test.command(name="persist")
    async def persist(self, ctx: commands.Context):
        """Creates a persistent view."""
        await ctx.send("What's your favourite colour?",
                       view=PersistentView(self.bot))


async def setup(bot: DiscordBot) -> None:
    await bot.add_cog(Test(bot))
