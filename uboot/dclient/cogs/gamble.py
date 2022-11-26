import random

import discord
from discord.ext import commands
from discord.ext.commands import param

from managers import users
from dclient import DiscordBot
from dclient.helper import get_member


def roll_dice() -> int:
    return (random.randint(1, 6), random.randint(1, 6))


class Gamble(commands.Cog):
    def __init__(self, bot: DiscordBot) -> None:
        self.bot = bot

    @commands.group(name="gamble")
    @commands.guild_only()
    async def gamble(self, ctx: commands.Context) -> None:
        """Gambling!"""
        if not ctx.invoked_subcommand:
            await ctx.send('invalid gamble command.')

    @gamble.command(name="show")
    async def show(self, ctx: commands.Context) -> None:
        """Shows the leaderboard."""
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

    @gamble.command(name="stats")
    async def stats(self, ctx: commands.Context):
        """Shows all of the user statistics."""
        user = users.Manager.get(ctx.author.id)

        win_rate = 0
        if user.gambles > 0:
            win_rate = (1 + (user.gambles_won - user.gambles) /
                        user.gambles) * 100

        embed = discord.Embed(title=ctx.author)
        embed.add_field(name="Gambling Stats", value='-' * 32, inline=False)
        embed.add_field(name="Gold", value=user.gold)
        embed.add_field(name="Messages", value=user.msg_count)
        embed.add_field(name="ㅤ", value="ㅤ")
        embed.add_field(name="Gambles", value=user.gambles)
        embed.add_field(name="Wins", value=user.gambles_won)
        embed.add_field(name="Win-Rate", value=f"{win_rate:0.2f}%")
        embed.add_field(name="ㅤ", value='-' * 32, inline=False)
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.set_footer(text=f"Id: {user.id}")

        await ctx.send(embed=embed)

    @commands.is_owner()
    @commands.command(name="give")
    async def give(self, ctx: commands.Context,
                   amount: int = param(description="Amount to give."),
                   to: discord.Member = param(description="Recipient")):
        """Give or remove gold from a user."""
        user = users.Manager.get(to.id)
        user.gold += amount
        self.bot._db.user.update(user)

        text = "increased by" if amount >= 0 else "reduced by"
        await ctx.send(f"{to} holdings were {text} "
                       f"{abs(amount)}gp by {ctx.author}.")

    @commands.guild_only()
    @commands.command(name="bet")
    async def bet(self, ctx: commands.Context,
                  amount: int = param(description="Amount to bet. 20gp min."),
                  side: str = param(description="High, low, or seven")):
        """Place a bet in a game of dice."""
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
        if side.lower() == "high" and total > 7:
            winnings = amount
        if side.lower() == "low" and total < 7:
            winnings = amount
        if side.lower() in ("seven", "7") and total == 7:
            winnings = amount * 4

        change = -1 * amount
        res = f"You lost {amount}gp"
        if winnings > 0:
            user.gambles_won += 1
            change = winnings
            res = f"You won {winnings}gp"
        user.gold += change
        user.gambles += 1
        self.bot._db.user.update(user)

        msg = f"Current gamble amount: {amount}gp.\n"\
            f"❊**{ctx.author}** rolls {dice[0]}, {dice[1]}❊\n"\
            f"Totaling {total}!\n\n{res}. Current holdings: {user.gold}gp."

        await ctx.send(msg)


async def setup(bot: DiscordBot) -> None:
    await bot.add_cog(Gamble(bot))
