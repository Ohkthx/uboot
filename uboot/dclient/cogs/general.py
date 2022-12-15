"""General commands that fit no particular category."""
import random
from datetime import datetime
from typing import Optional

import discord
from discord.ext import commands
from discord.ext.commands import param

from dclient import DiscordBot
from dclient.views.embeds import EmbedView

# All standard magic 8 ball options.
eight_ball_opts = [["It is certain.", "It is decidely so.", "Without a doubt.",
                    "Yes definitely.", "You may rely on it.",
                    "As I see it, yes.", "Most likely.", "Outlook good.", "Yes",
                    "Signs point to yes."],
                   ["Reply hazy, try again.",
                       "Ask again later.", "Better not tell you now.",
                       "Cannot predict now.", "Concentrate and ask again."],
                   ["Don't count on it.", "My reply is no.",
                       "My sources say no.", "Outlook not so good.",
                       "Very doubtful."]]


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

    @commands.command(name="8ball", aliases=("8-ball", "magic-8ball", "shake"))
    async def eight_ball(self, ctx: commands.Context,
                         question: Optional[str] = param(
                             description="Question to ask.",
                             default='none')) -> None:
        """Shakes a magic 8-ball. Results are not final."""
        await ctx.message.delete()
        if len(ctx.message.mentions) > 0:
            await ctx.send("Mentioning others is not allowed while asking "
                           "a question.",
                           delete_after=15)
            return

        # Extracts the question from the raw message.
        lstrip = f"{ctx.prefix}{ctx.invoked_with} "
        question = ctx.message.content.lstrip(lstrip)
        asks = ''
        if len(question) > 0:
            asks = f' > "{question}"\n\n'

        # Get the text.
        quality = random.randrange(0, len(eight_ball_opts))
        pos = random.randrange(0, len(eight_ball_opts[quality]))
        phrase = eight_ball_opts[quality][pos]

        # Change the color of the embed based on the positivity.
        color = discord.Colour.from_str("#00ff08")
        if quality == 1:
            color = discord.Colour.from_str("#F1C800")
        if quality == 2:
            color = discord.Colour.from_str("#ff0f08")
        elif quality > 2:
            color = discord.Colour.default()

        embed = discord.Embed()
        embed.description = f"**{ctx.author}** shakes the magic 8-ball.\n"\
            f"{asks}"\
            f"```{phrase}```"
        embed.color = color
        embed.set_footer(text="disclaimer: works 50% of the time, every time.")
        await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.is_owner()
    @commands.command(name="powerhour", aliases=("ph",))
    async def powerhour(self, ctx: commands.Context) -> None:
        """Starts a powerhour for messages! 3x gold generation per message."""
        if not ctx.guild or not ctx.channel:
            return

        self.bot.start_powerhour(ctx.guild.id, ctx.channel.id, 3.0)
        embed = discord.Embed()
        embed.description = "__Message **POWERHOUR** started!__\n"\
            "> └ Gold generation per message is increased by 3x."
        embed.color = discord.Colour.from_str("#00ff08")
        embed.set_footer(text=f"Powerhour started by {ctx.author}")
        await ctx.send(embed=embed)

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
            # Message Id was passed, try to get the message.
            msg = await channel.fetch_message(msg_id)
            if not msg:
                await ctx.send("Could not find message by that id.",
                               delete_after=30)
                return

            # Prevent trying to edit other user messages.
            if self.bot.user and msg.author.id != self.bot.user.id:
                await ctx.send("Can only attach to the bots messages.",
                               delete_after=30)
                return

        view = EmbedView(ctx.author.id, msg)
        await ctx.send(view=view, delete_after=30)
        if ctx.message:
            await ctx.message.delete()


async def setup(bot: DiscordBot) -> None:
    """This is called by process that loads extensions."""
    await bot.add_cog(General(bot))
