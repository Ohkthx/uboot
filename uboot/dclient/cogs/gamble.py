import random
from datetime import datetime, timezone

import discord
from discord.ext import commands
from discord.ext.commands import param

from managers import users
from dclient import DiscordBot
from dclient.helper import get_member


def roll_dice() -> tuple[int, int]:
    return (random.randint(1, 6), random.randint(1, 6))


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
            win_rate = (1 + (u.gambles_won - u.gambles) /
                        u.gambles) * 100
            wr = f"Win-Rate: {win_rate:0.2f}%"
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
            # Get all of the gold lost from users.
            total: int = 0
            for u in users.Manager.getall():
                if u.gold < u.msg_count:
                    total += (u.msg_count - u.gold)
            gold_t = total

        win_rate = 0
        if user_l.gambles > 0:
            win_rate = (1 + (user_l.gambles_won - user_l.gambles) /
                        user_l.gambles) * 100

        age = datetime.now(timezone.utc) - user.created_at
        year_str = '' if age.days // 365 < 1 else f"{age.days//365} year(s), "
        day_str = '' if age.days % 365 == 0 else f"{int(age.days%365)} day(s)"

        desc = f"**{user}{title}**\n\n"\
            f"**user id**: `{user.id}`\n"\
            f"**age**: `{year_str}{day_str}`\n"\
            f"**gold**: `{gold_t} gp`\n"\
            f"**messages**: `{user_l.msg_count}`\n\n"\
            "> __Gambles__:\n"\
            f"> ├ **total**: `{user_l.gambles}`\n"\
            f"> ├ **won**: `{user_l.gambles_won}`\n"\
            f"> └ **win-rate**: `{win_rate:0.2f}%`\n"

        embed = discord.Embed(description=desc)
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
        self.bot._db.user.update(user)

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

        self.bot._db.user.update(from_user)
        self.bot._db.user.update(to_user)

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
            (prefix)bet 40 low"""
        if amount <= 0:
            await ctx.send("cannot be 0 or less.")
            return

        valid_input = ("high", "low", "seven", "7")
        if side.lower() not in valid_input:
            await ctx.send("You must choose: high, low, or seven")
            return

        user = users.Manager.get(ctx.author.id)
        if amount > user.gold:
            amount = user.gold

        minimum_offset = int(user.gold * 0.1)
        minimum = minimum_offset if minimum_offset > 20 else 20
        if amount < minimum:
            res = f"You must reach the minimum bet of {minimum}gp!\n"\
                f"Current holdings: {user.gold}gp."
            await ctx.send(res)
            return

        # Gamble here.
        dice = roll_dice()
        total = dice[0] + dice[1]

        winnings: int = 0
        res_status: str = "high"
        if total < 7:
            res_status = "low"
        elif total == 7:
            res_status = "seven"

        if side.lower() == "high" and total > 7:
            winnings = amount
        if side.lower() == "low" and total < 7:
            winnings = amount
        if side.lower() in ("seven", "7") and total == 7:
            winnings = amount * 4

        change = -1 * amount
        res = f"You **lost** {amount}gp"
        if winnings > 0:
            user.gambles_won += 1
            change = winnings
            res = f"You **won** {winnings}gp"
        user.gold += change
        user.gambles += 1
        self.bot._db.user.update(user)

        if self.bot.user:
            bot_user = users.Manager.get(self.bot.user.id)
            bot_user.gambles += 1
            if winnings == 0:
                bot_user.gambles_won += 1
            self.bot._db.user.update(bot_user)

        msg = f"Current gamble amount: {amount}gp on **{side.lower()}**.\n"\
            f"❊**{ctx.author}** rolls {dice[0]}, {dice[1]}❊\n"\
            f"Totaling {total}! Result is **{res_status}**.\n\n"\
            f"{res}. Current holdings: {user.gold}gp."

        await ctx.send(msg)


async def setup(bot: DiscordBot) -> None:
    await bot.add_cog(Gamble(bot))
