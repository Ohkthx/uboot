import discord
from discord.ext import commands

from dclient import DiscordBot
from dclient.helper import find_tag, thread_close, get_member


class Threads(commands.Cog):
    """Thread management for manually assigning thread status."""

    def __init__(self, bot: DiscordBot) -> None:
        self.bot = bot
        self.delete_after = 5.0

    @commands.guild_only()
    @commands.group(name="thread")
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

    @thread.command(name='leave')
    async def leave(self, ctx: commands.Context) -> None:
        """Leave a thread. Later losers."""
        if not isinstance(ctx.channel, discord.Thread):
            return

        if not isinstance(ctx.channel.parent, discord.ForumChannel):
            await ctx.message.delete()
            await ctx.send('thread is not in a forum channel.',
                           delete_after=self.delete_after)
            return

        await ctx.channel.remove_user(ctx.author)

    @thread.command(name='isdone')
    @commands.has_guild_permissions(manage_messages=True)
    async def isdone(self, ctx: commands.Context) -> None:
        """Prompts the members if the thread is complete or not."""
        await ctx.send("Is the thread ready to be permanently closed?\n"
                       "If so, please type `?thread close`")
        await ctx.message.delete()

    @thread.command(name='open')
    @commands.has_guild_permissions(manage_messages=True)
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

    @thread.command(name='close')
    async def close(self, ctx: commands.Context) -> None:
        """Unsubscribes all users, closes, and archives the current thread."""
        if not isinstance(ctx.channel, discord.Thread) or not ctx.guild:
            return

        owner_id = ctx.channel.owner_id
        author = await get_member(self.bot, ctx.guild.id, ctx.author.id)
        if not author:
            return

        if owner_id != author.id and not author.guild_permissions.manage_messages:
            msg = "only the owner of the thread or an admin can close thread."
            await ctx.send(msg)
            return

        reason = f"thread close command called by {author} {author.id}"
        user_msg = f"Your thread '{ctx.channel.name}' was closed"
        if ctx.guild and owner_id:
            owner = await get_member(self.bot, ctx.guild.id, owner_id)
            if owner:
                user_msg = f"{user_msg} by {author}"

        await ctx.channel.send(f"Thread closed by {author}.")
        await ctx.message.delete()
        await thread_close('open', 'closed', ctx.channel, reason,
                           f"{user_msg}.")


async def setup(bot: DiscordBot) -> None:
    await bot.add_cog(Threads(bot))
