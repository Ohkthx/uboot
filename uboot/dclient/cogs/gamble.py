import random
from datetime import datetime, timezone

import discord
from discord.ext import commands
from discord.ext.commands import param

from managers import users, settings
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
        (prefix)bet 40 low
    """

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
            winrate = f"Win-Rate: {u.win_rate():0.2f}%"
            user_board.append(f"{pos}: **{user}** - {u.gold} gp - {winrate}")
        summary = "\n".join(user_board)
        color = discord.Colour.from_str("#00ff08")
        embed = discord.Embed(title="Top 10 Gamblers",
                              description=summary, color=color)
        embed.set_footer(text=f"Total gamblers: {len(all_users)}")
        await ctx.send(embed=embed)

    @commands.command(name="stats", aliases=("balance", "statement"))
    async def stats(self, ctx: commands.Context,
                    user: discord.User = param(
                        description="Optional Id of the user to lookup.",
                        default=lambda ctx: ctx.author,
                        displayed_default="self")):
        """Shows statistics for a specified user, defaults to you.
        examples:
            (prefix)stats
            (prefix)stats @Gatekeeper
            (prefix)stats 1044706648964472902
        """
        user_l = users.Manager.get(user.id)
        title = '' if user_l.button_press == 0 else ', the Button Presser'

        if self.bot.user and self.bot.user.id == user.id:
            title = ', the Scholar'

        age = datetime.now(timezone.utc) - user.created_at
        year_str = '' if age.days // 365 < 1 else f"{age.days//365} year(s), "
        day_str = '' if age.days % 365 == 0 else f"{int(age.days%365)} day(s)"

        color = discord.Colour.from_str("#00ff08")
        desc = f"**{user}{title}**\n\n"\
            f"**id**: {user.id}\n"\
            f"**age**: {year_str}{day_str}\n"\
            f"**gold**: {user_l.gold} gp\n"\
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
            (prefix)spawn 40 @Gatekeeper
        """
        user = users.Manager.get(to.id)
        user.gold += amount
        user.save()

        color = discord.Color.from_str("#F1C800")
        title = "Transaction Receipt"
        status = "Increased by" if amount >= 0 else "Reduced by"
        desc = f"**To**: {to}\n"\
            f"**From**: {ctx.author}\n"\
            f"**Amount**: {amount} gp\n\n"\
            f"{status} {abs(amount)} gp from {ctx.author}."
        embed = discord.Embed(title=title, description=desc, color=color)
        embed.set_footer(text="transaction type: spawn")

        await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.command(name="give", aliases=("withdraw",))
    async def give(self, ctx: commands.Context,
                   amount: int = param(description="Amount to give."),
                   to: discord.Member = param(description="Recipient")):
        """Give gold from yourself to another user.
        example:
            (prefix)give 40 @Gatekeeper
        """
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

        color = discord.Color.from_str("#F1C800")
        title = "Transaction Receipt"
        status = "Increased by" if amount >= 0 else "Reduced by"
        desc = f"**To**: {to}\n"\
            f"**From**: {ctx.author}\n"\
            f"**Amount**: {amount} gp\n\n"\
            f"{status} {abs(amount)} gp from {ctx.author}."
        embed = discord.Embed(title=title, description=desc, color=color)
        embed.set_footer(text="transaction type: give")

        await ctx.send(embed=embed)

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
        await self.bot.rm_user_destructable(user.id)

        old_gold = user.gold
        results = gamble(user, str(ctx.author), amount, side)
        if results.iserror:
            color = discord.Colour.from_str(color_hex)
            embed = discord.Embed(description=results.msg, color=color)
            return await ctx.send(embed=embed, delete_after=60)

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
            destructable = DestructableView(msg, user.id, 300)
            self.bot.add_destructable(destructable)

    @commands.guild_only()
    @commands.has_guild_permissions(manage_messages=True)
    @commands.command(name="lotto")
    async def lotto(self, ctx: commands.Context,
                    amount: int = param(description="Amount of winners."),
                    ) -> None:
        """Performs the lotto assigning all users with the defined lotto role
        a new winner lotto role.

        example:
            (prefix)lotto 10
        """
        guild = ctx.guild
        if not guild:
            return

        if amount <= 0:
            await ctx.send("Need more than 0 winners picked.")
            return

        setting = settings.Manager.get(guild.id)

        # Get lotto role.
        lotto_role = guild.get_role(setting.lotto_role_id)
        if not lotto_role:
            await ctx.send("Lotto role could not be found.")
            return

        # Get lotto winner role.
        winner_role = guild.get_role(setting.lotto_winner_role_id)
        if not winner_role:
            await ctx.send("Winner role could not be found.")
            return

        # Perform Lotto.
        lotto_pool: list[discord.Member] = []
        for member in lotto_role.members:
            if member in winner_role.members:
                continue
            if winner_role in member.roles:
                continue
            lotto_pool.append(member)

        winners: list[discord.Member] = []
        if amount >= len(lotto_pool):
            winners = lotto_pool
        else:
            while len(winners) < amount:
                if len(lotto_pool) == 0:
                    break

                pos = random.randrange(0, len(lotto_pool))
                user = lotto_pool[pos]
                if not user:
                    continue

                if winner_role not in user.roles:
                    winners.append(user)
                lotto_pool = [u for u in lotto_pool if u.id != user.id]

        title = "__**Lotto Winners!**__"
        if len(winners) == 0:
            await ctx.send(f"{title}\n> └ No Winners.")
            return

        # Assign the winner.
        winner_text: list[str] = []
        for n, winner in enumerate(winners):
            lf = '└' if n + 1 == len(winners) else '├'
            winner_text.append(f"> {lf} {winner.mention} (**{winner}**)")
            if lotto_role in winner.roles:
                try:
                    await winner.remove_roles(lotto_role)
                except BaseException:
                    pass
            try:
                await winner.add_roles(winner_role)
            except BaseException:
                pass

        full_text = '\n'.join(winner_text)
        # Format and print winners.
        await ctx.send(f"{title}\n{full_text}\n\n"
                       f"Congratulations on your new role: **{winner_role}**")


async def setup(bot: DiscordBot) -> None:
    await bot.add_cog(Gamble(bot))
