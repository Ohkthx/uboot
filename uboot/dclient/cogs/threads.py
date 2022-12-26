"""Commands used to manage discord threads or add additional functionality to
them. Most of these commands are reseved for staff/admins.
"""
import discord
from discord.ext import commands

from dclient import DiscordBot
from dclient.helper import find_tag, thread_close, get_member
from dclient.views.dm import DMDeleteView


class Threads(commands.Cog):
    """Thread management for manually assigning thread status.
    Additional 'help' information:
        (prefix)help thread
        (prefix)help thread [command]
    """

    def __init__(self, bot: DiscordBot) -> None:
        self.bot = bot
        self.delete_after = 5.0

    @commands.guild_only()
    @commands.group(name="thread")
    async def thread(self, ctx: commands.Context) -> None:
        """Thread management for manually assigning thread status.
        Additional 'help' information:
            (prefix)help thread [command]

        examples:
            (prefix)thread open
            (prefix)thread close
        """
        # Check to make sure this is a thread it is being called in.
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
        # Check to make sure this is a thread it is being called in.
        if not isinstance(ctx.channel, discord.Thread):
            return

        # Requires the thread to be in a Forum Channel.
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
                       f"If so, please type `{self.bot.prefix}thread close`")
        await ctx.message.delete()

    @thread.command(name='open')
    @commands.has_guild_permissions(manage_messages=True)
    async def open(self, ctx: commands.Context) -> None:
        """Marks a thread with the open tag."""
        # Check to make sure this is a thread it is being called in.
        if not isinstance(ctx.channel, discord.Thread):
            return

        # Requires the thread to be in a Forum Channel.
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
        """Performs a full clean up and closure on the thread.
        Actions:
            Unsubscribes all participants in the thread.
            Marks the thread with the 'close' tag if it is available.
            Removes the 'open' tag if it is assigned.
            Closes the thread.
            Locks the thread.
        """
        # Check to make sure this is a thread it is being called in.
        if not isinstance(ctx.channel, discord.Thread) or not ctx.guild:
            return

        # Get the owner of the thread.
        owner_id = ctx.channel.owner_id
        author = await get_member(self.bot, ctx.guild.id, ctx.author.id)
        if not author:
            return

        # Deny the user if they are not an owner or staff/admins with
        # permissions.
        if owner_id != author.id and not author.guild_permissions.manage_messages:
            msg = "only the owner of the thread or an admin can close thread."
            await ctx.send(msg)
            return

        reason = f"thread close command called by {author} {author.id}"

        # Send the closure text and close, lock, and archive the thread.
        await ctx.channel.send(f"Thread closed by {author}.")
        await ctx.message.delete()
        await thread_close(['open', 'in-progress'], 'closed',
                           ctx.channel, reason)

        owner = await get_member(self.bot, ctx.guild.id, owner_id)
        if not owner:
            return

        view = DMDeleteView(self.bot)
        user_msg = f"Your thread '{ctx.channel.name}' was closed by {author}"
        await owner.send(content=user_msg, view=view)


async def setup(bot: DiscordBot) -> None:
    """This is called by process that loads extensions."""
    await bot.add_cog(Threads(bot))
