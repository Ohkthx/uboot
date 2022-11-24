import discord
from discord.ext import commands

from dclient import DiscordBot
from dclient.helper import find_tag, thread_close, get_member


class Threads(commands.Cog):
    """Thread management for manually assigning thread status."""

    def __init__(self, bot: DiscordBot) -> None:
        self.bot = bot
        self.delete_after = 5.0

    @commands.group(name="thread")
    @commands.has_guild_permissions(manage_messages=True)
    async def thread(self, ctx: commands.Context) -> None:
        """Thread management for manually assigning thread status."""
        if not isinstance(ctx.channel, discord.Thread):
            await ctx.message.delete()
            await ctx.send("cannot be used outside of a thread.",
                           delete_after=self.delete_after)
            return
        if not ctx.invoked_subcommand:
            await ctx.send('invalid thread command.',
                           delete_after=self.delete_after)

    @thread.command(name='open')
    async def open(self, ctx: commands.Context) -> None:
        """Marks a thread with the open tag."""
        if not isinstance(ctx.channel, discord.Thread):
            return

        if not isinstance(ctx.channel.parent, discord.ForumChannel):
            await ctx.message.delete()
            await ctx.send('thread is not in a forum channel.',
                           delete_after=self.delete_after)
            return

        # Find the open tag from available tags and apply it.
        open_tag = find_tag("open", ctx.channel.parent)
        if not open_tag:
            await ctx.send("'open' tag is not available in this thread.",
                           delete_after=self.delete_after)
        elif open_tag not in ctx.channel.applied_tags:
            await ctx.channel.add_tags(open_tag)

        await ctx.message.delete()

    @thread.command(name='close')
    async def close(self, ctx: commands.Context) -> None:
        """Unsubscribes all users, closes, and archives the current thread."""
        if not isinstance(ctx.channel, discord.Thread):
            return

        reason = f"thread close command called by {ctx.author} {ctx.author.id}"
        user_msg = f"Your thread '{ctx.channel.name}' was closed"
        if ctx.guild and ctx.channel.owner_id:
            owner = await get_member(self.bot, ctx.guild.id,
                                     ctx.channel.owner_id)
            if owner:
                user_msg = f"{user_msg} by {ctx.author}"

        await ctx.channel.send(f"Thread closed by {ctx.author}.")
        await ctx.message.delete()
        await thread_close('open', 'closed', ctx.channel, reason,
                           f"{user_msg}.")


async def setup(bot: DiscordBot) -> None:
    await bot.add_cog(Threads(bot))
