"""General commands that fit no particular category."""
import random
from datetime import datetime
from typing import Optional

import discord
from discord.ext import commands
from discord.ext.commands import param

from dclient import DiscordBot
from dclient.helper import get_message, get_channel
from dclient.views.embeds import EmbedView
from dclient.views.user import RockPaperScissorsView
from dclient.destructable import Destructable
from managers import aliases, settings

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


async def get_alias_embed(client: discord.Client,
                          alias: aliases.Alias) -> Optional[discord.Embed]:
    """Attempts to get the embed from the message bank."""
    # Get the message the reactions are attached to.
    bank_id = settings.Manager.get(alias.guild_id).alias.channel_id
    msg = await get_message(client, bank_id, alias.msg_id)
    if not msg:
        return

    if len(msg.embeds) > 0:
        return msg.embeds[0]


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
    async def powerhour(self, ctx: commands.Context,
                        length: int = param(description="How many hours of "
                                            "powerhour.", default=1)) -> None:
        """Starts a powerhour for messages! 3x gold generation per message."""
        if not ctx.guild or not ctx.channel:
            return

        if length <= 0:
            await ctx.send("Length of powerhour has to be more than 0.",
                           delete_after=30)
            return

        if not isinstance(ctx.channel, discord.TextChannel):
            await ctx.send("That command must be used in a normal text "
                           "channel.",
                           delete_after=15)
            return

        self.bot.start_powerhour(ctx.guild.id, ctx.channel.id, 3.0, length)
        embed = discord.Embed()
        embed.description = "__**Message POWERHOUR started!**__\n"\
            "> ├ Gold generation per message is increased by 3x.\n"\
            f"> └ Hours Active: {length}"
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

    @commands.command(name="rps")
    async def rps(self, ctx: commands.Context) -> None:
        """Play a game of rock, paper, and scissors!"""
        if not ctx.guild:
            return

        embed = RockPaperScissorsView.get_panel()
        view = RockPaperScissorsView(self.bot)
        message = await ctx.send(embed=embed, view=view)
        if view and message and self.bot.user:
            category = Destructable.Category.OTHER
            destruct = Destructable(category, self.bot.user.id, 30)
            destruct.set_message(message=message)
            destruct.set_callback(view.callback)

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

        if not isinstance(channel, (discord.Thread, discord.TextChannel)):
            await ctx.send("The channel has to be either a thread or text "
                           "channel where embeds can be sent.",
                           delete_after=30)
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

        panel = EmbedView.get_panel()
        view = EmbedView(ctx.author.id, channel, msg)
        await ctx.author.send(embed=panel, view=view, delete_after=120)
        if ctx.message:
            await ctx.message.delete()

    @commands.guild_only()
    @commands.group("alias")
    async def alias(self, ctx: commands.Context) -> None:
        """Group of alias commands that are used to post information. Aliases
        are attached to embeds that send the embed that is linked.

        examples:
            (prefix)alias add hello_world 0123456789
            (prefix)alias show
            (prefix)alias hello_world
            (prefix)alias remove hello_world
        """
        if ctx.invoked_subcommand:
            return

        # Attempt to find the alias.
        alias_name = ctx.subcommand_passed
        if not alias_name or not ctx.guild:
            await ctx.send("invalid alias command.", delete_after=30)
            return

        alias = aliases.Manager.by_name(ctx.guild.id, alias_name.lower())
        if not alias:
            await ctx.send("invalid alias command.", delete_after=30)
            return

        embed = await get_alias_embed(self.bot, alias)
        if not embed:
            await ctx.send("alias broken, embed missing.", delete_after=30)
            return

        await ctx.message.delete()
        await ctx.send(embed=embed)

    @commands.has_permissions(manage_channels=True)
    @alias.command("add")
    async def add(self, ctx: commands.Context,
                  name: str, message_id: int) -> None:
        """Add a new alias that attaches to an embed. When the alias is called,
        the associated embed will be sent.

        examples:
            (prefix)alias add test 0123456789
        """
        if not ctx.guild:
            return

        if name in ("add", "rm", "remove", "show", "display", "print"):
            await ctx.reply("You cannot add an alias with that name.",
                            delete_after=30)
            return

        # Check if name exists.
        alias = aliases.Manager.by_name(ctx.guild.id, name.lower())
        if alias:
            await ctx.reply("Alias is already set.", delete_after=30)
            return

        setting = settings.Manager.get(ctx.guild.id)
        bank_id = setting.alias.channel_id
        if bank_id <= 0:
            await ctx.send("embed bank channel id is unset, please set it "
                           "with settings command.")
            return

        # Check that the channel exists.
        channel = await get_channel(self.bot, bank_id)
        if not channel:
            await ctx.send("channel for the bank does not exist.",
                           delete_after=30)
            return

        if message_id <= 0:
            await ctx.send("message id has to be greater than 0.",
                           delete_after=30)
            return

        # Get the message the reactions are attached to.
        msg = await get_message(self.bot, bank_id, message_id)
        if not msg:
            await ctx.send("could not identify the message.")
            return

        last_id = aliases.Manager.last_id(ctx.guild.id)
        alias = aliases.Manager.get(ctx.guild.id, last_id + 1)
        alias.msg_id = message_id
        alias.name = name.lower()
        alias.owner_id = ctx.author.id
        alias.save()

        embed = discord.Embed(title="Alias Created")
        embed.color = discord.Color.blurple()
        embed.description = f"Done! **{name.lower()}** alias added to "\
            f"[message]({msg.jump_url})."
        await ctx.send(embed=embed, delete_after=120)

    @commands.has_permissions(manage_channels=True)
    @alias.command("remove", aliases=("rm",))
    async def remove(self, ctx: commands.Context,
                     name: str) -> None:
        """Remove an alias

        examples:
            (prefix)alias remove test
            (prefix)alias rm hello_world
        """
        if not ctx.guild:
            return

        success = aliases.Manager.remove(ctx.guild.id, name.lower())
        await ctx.send(f"Alias removal success: {str(success).lower()}")

    @alias.command("show", aliases=("print", "display"))
    async def show(self, ctx: commands.Context) -> None:
        """Shows all aliases for the server.

        examples:
            (prefix)alias show
        """
        if not ctx.guild:
            return

        embed = discord.Embed()
        embed.color = discord.Colour.from_str("#ff0f08")
        all_alias = aliases.Manager.get_all(ctx.guild.id)
        if len(all_alias) == 0:
            embed.description = "There are no aliases set."
            await ctx.send(embed=embed)
            return

        alias_str: list[str] = []
        for alias in all_alias:
            alias_str.append(f"> {str(alias)}")

        full_text: str = '\n'.join(alias_str)
        embed.color = discord.Colour.from_str("#00ff08")
        embed.description = f"__**Current Aliases**__:\n{full_text}"

        await ctx.send(embed=embed)


async def setup(bot: DiscordBot) -> None:
    """This is called by process that loads extensions."""
    await bot.add_cog(General(bot))
