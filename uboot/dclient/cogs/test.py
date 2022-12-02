import discord
from discord.ext import commands

from dclient import DiscordBot
from dclient.views.test import PersistentView
from dclient.views.red_button import RedButtonView


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

    @test.command(name="red-button")
    async def red_button(self, ctx: commands.Context):
        """Creates the red button view."""
        await ctx.message.delete()
        embed = RedButtonView.get_panel()
        await ctx.send(embed=embed, view=RedButtonView())


async def setup(bot: DiscordBot) -> None:
    await bot.add_cog(Test(bot))
