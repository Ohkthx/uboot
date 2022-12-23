"""Commands that are currently being tested."""

import discord
from discord.ext import commands

from dclient import DiscordBot
from dclient.helper import get_role
from dclient.views.test import PersistentView
from dclient.views.red_button import RedButtonView
from managers import entities, users, settings


class Test(commands.Cog):
    """For testing new ideas."""

    def __init__(self, bot: DiscordBot) -> None:
        self.bot = bot

    @commands.is_owner()
    @commands.guild_only()
    @commands.group(name="test")
    async def test(self, ctx: commands.Context) -> None:
        """Group of test commands that are not officially implemented yet."""
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
        last = await ctx.send(embed=embed, view=RedButtonView(self.bot))
        self.bot.last_button = last

    @test.command(name="spawn")
    async def spawn(self, ctx: commands.Context):
        """Spawns a monster."""
        if not ctx.guild or not isinstance(ctx.author, discord.Member):
            return await ctx.reply("Could not identify user.", delete_after=15)

        # Check that the user has the minigame role.
        setting = settings.Manager.get(ctx.guild.id)
        role_id = setting.minigame_role_id
        minigame_role = await get_role(self.bot, ctx.guild.id, role_id)
        if not minigame_role:
            await ctx.reply("Minigame role may be current unset.",
                            delete_after=30)
            return

        # User does not have the role and cannot play.
        if minigame_role not in ctx.author.roles:
            # Shows and optional text for easy role access.
            in_channel: str = ""
            if setting.react_role_channel_id > 0:
                in_channel = f"\nGo to <#{setting.react_role_channel_id}> to get the"\
                    " required role."
            await ctx.reply(f"You need to select the **{minigame_role}** role "
                            f"to do that. {in_channel}", delete_after=30)
            return

        user_l = users.Manager.get(ctx.author.id)
        if user_l.incombat:
            return await ctx.reply("You are already in combat.",
                                   delete_after=15)
        entity = entities.Manager.spawn(user_l.c_location, user_l.difficulty)
        if entity:
            await self.bot.add_entity(ctx.message, ctx.author, entity)


async def setup(bot: DiscordBot) -> None:
    """This is called by process that loads extensions."""
    await bot.add_cog(Test(bot))
