import random
from datetime import datetime, timezone

import discord
from discord.ext import commands
from discord.ext.commands import param

from managers import users
from dclient import DiscordBot, DestructableView
from dclient.helper import get_member
from dclient.views.gamble import GambleView, gamble


class Gamble(commands.Cog):
    """Betting Guideline:
    You have three options, 'high', 'low', or 'seven'.
    The result is the total from 2 dice rolls.
        High:  8-12    with a 1:1 payout.
        Low:   1-6     with a 1:1 payout.
        Seven: 7       with a 4:1 payout.

    example:
        (prefix)bet 40 low"""

    def __init__(self, bot: DiscordBot) -> None:
        self.bot = bot

    @commands.guild_only()
    @commands.command(name="leaderboard")
    async def leaderboard(self, ctx: commands.Context) -> None:
        """Shows the current gambling leaderboard."""
        if not ctx.guild:
            return
        all_users = users.Manager.getall()
        all_users = list(filter(lambda u: u.gambles > 0, all_users))
        all_users.sort(key=lambda u: u.gold, reverse=True)

        pos: int = 0
        user_board: list[str] = []
        for u in all_users:
            if pos >= 10:
                break

            user = await get_member(self.bot, ctx.guild.id, u.id)
            if not user:
                continue
            pos += 1
            wr = f"Win-Rate: {u.win_rate():0.2f}%"
            user_board.append(f"{pos}: **{user}** - {u.gold}gp - {wr}")
        summary = "\n".join(user_board)
        embed = discord.Embed(title="Top 10 Gamblers",
                              description=summary)
        embed.set_footer(text=f"Total gamblers: {len(all_users)}")
        await ctx.send(embed=embed)

    @commands.command(name="stats")
    async def stats(self, ctx: commands.Context,
                    user: discord.User = param(
                        description="Optional Id of the user to lookup.",
                        default=lambda ctx: ctx.author,
                        displayed_default="self")):
        """Shows statistics for a specified user, defaults to you.
        examples:
            (prefix)stats
            (prefix)stats @Gatekeeper
            (prefix)stats 1044706648964472902"""
        user_l = users.Manager.get(user.id)
        title = '' if user_l.button_press == 0 else ', the Button Presser'

        gold_t = user_l.gold
        if self.bot.user and self.bot.user.id == user.id:
            title = ', the Scholar'
            # Get all of the gold lost from nusers.
            total: int = 0
            for u in users.Manager.getall():
                if u.gold < u.msg_count:
                    total += (u.msg_count - u.gold)
            gold_t = total

        age = datetime.now(timezone.utc) - user.created_at
        year_str = '' if age.days // 365 < 1 else f"{age.days//365} year(s), "
        day_str = '' if age.days % 365 == 0 else f"{int(age.days%365)} day(s)"

        color = discord.Colour.from_str("#00ff08")
        desc = f"**{user}{title}**\n\n"\
            f"**id**: {user.id}\n"\
            f"**age**: {year_str}{day_str}\n"\
            f"**gold**: {gold_t} gp\n"\
            f"**messages**: {user_l.msg_count}\n\n"\
            "> __Gamble__:\n"\
            f"> ├ **total**: {user_l.gambles}\n"\
            f"> ├ **won**: {user_l.gambles_won}\n"\
            f"> ├ **win-rate**: {user_l.win_rate():0.2f}%\n"\
            f"> └ **minimum**: {user_l.minimum(20)} gp\n"

        embed = discord.Embed(description=desc, color=color)
        embed.set_thumbnail(url=user.display_avatar.url)

        await ctx.send(embed=embed)

    @commands.is_owner()
    @commands.command(name="spawn")
    async def spawn(self, ctx: commands.Context,
                    amount: int = param(description="Amount to spawn."),
                    to: discord.Member = param(description="Recipient")):
        """Give or remove gold from a user.
        example:
            (prefix)spawn 40 @Gatekeeper"""
        user = users.Manager.get(to.id)
        user.gold += amount
        user.save()

        text = "increased by" if amount >= 0 else "reduced by"
        await ctx.send(f"{to} holdings were {text} "
                       f"{abs(amount)}gp by {ctx.author}.")

    @commands.guild_only()
    @commands.command(name="give")
    async def give(self, ctx: commands.Context,
                   amount: int = param(description="Amount to give."),
                   to: discord.Member = param(description="Recipient")):
        """Give gold from yourself to another user.
        example:
            (prefix)give 40 @Gatekeeper"""
        from_user = users.Manager.get(ctx.author.id)
        if amount > from_user.gold:
            amount = from_user.gold

        if amount <= 0:
            await ctx.send(f"{amount}gp is not a valid gold amount to send.")
            return

        to_user = users.Manager.get(to.id)
        if from_user.id == to_user.id:
            msg = "What would be the purpose in sending gold to yourself?"
            await ctx.send(msg)
            return

        from_user.gold -= amount
        to_user.gold += amount

        from_user.save()
        to_user.save()

        text = "increased by" if amount >= 0 else "reduced by"
        await ctx.send(f"{to} holdings were {text} "
                       f"{abs(amount)}gp by {ctx.author}.")

    @commands.guild_only()
    @commands.command(name="bet")
    async def bet(self, ctx: commands.Context,
                  amount: int = param(description="Amount to bet. 20gp min."),
                  side: str = param(description="High, low, or seven")):
        """Place your bet, requires an amount and position (high, low, seven)
        The amount required is either 20gp OR 10% of your current gold.

        Check your current gold with: (prefix)stats
        example:
            (prefix)bet 40 low
        """

        view = None
        color_hex = "#ff0f08"  # Loss color.
        user = users.Manager.get(ctx.author.id)
        old_gold = user.gold
        results = gamble(user, str(ctx.author), amount, side)
        if results.iserror:
            color = discord.Colour.from_str(color_hex)
            embed = discord.Embed(description=results.msg, color=color)
            return await ctx.send(embed=embed)

        user.save()
        if results.winnings > 0:
            view = GambleView(self.bot, user, 300,
                              results.winnings, side,
                              old_gold)
            color_hex = "#00ff08"

        if self.bot.user:
            bot_user = users.Manager.get(self.bot.user.id)
            bot_user.gambles += 1
            if results.winnings == 0:
                bot_user.gambles_won += 1
            bot_user.save()

        color = discord.Colour.from_str(color_hex)
        embed = discord.Embed(description=results.msg, color=color)
        embed.set_footer(text=f"Next minimum: {user.minimum(20)} gp")
        msg = await ctx.send(embed=embed, view=view)
        if view:
            # Schedule to delete the view.
            self.bot.destructables[msg.id] = DestructableView(msg,
                                                              user.id,
                                                              300)


async def setup(bot: DiscordBot) -> None:
    await bot.add_cog(Gamble(bot))
