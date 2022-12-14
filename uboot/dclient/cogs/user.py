"""Various commands that support the gambling mechanic."""
import random
from datetime import datetime, timezone

import discord
from discord.ext import commands
from discord.ext.commands import param

from managers import users, settings
from dclient import DiscordBot
from dclient.destructable import DestructableManager, Destructable
from dclient.helper import get_member, get_role, get_user
from dclient.views.gamble import GambleView, gamble, ExtractedBet
from dclient.views.dm import DMDeleteView
from dclient.views.user import UserView


def parse_amount(amount: str) -> int:
    """Wrapper for attempting to pull a value from a string."""
    try:
        return int(amount)
    except BaseException:
        return -1


def extract_bet(arg1: str, arg2: str) -> ExtractedBet:
    """Converts two string values into a bet. This tries to resolve special
    parameters passed such as, 'all', 'min', and '7' as well.
    """
    res: ExtractedBet = ExtractedBet(-1, '', False, False)

    # Checks for an all-in bet.
    if 'all' in (arg1.lower(), arg2.lower()):
        res.is_all = True
        if 'all' == arg1.lower():
            res.side = arg2
        else:
            res.side = arg1
        return res

    # Checks for the minimum being bet.
    if 'min' in (arg1.lower(), arg2.lower()):
        res.minimum = True
        if 'min' == arg1.lower():
            res.side = arg2
        else:
            res.side = arg1
        return res

    # Check for the '7' override / shortcut.
    if '7' in (arg1.lower(), arg2.lower()):
        res.side = "seven"
        if '7' in arg1.lower():
            res.amount = parse_amount(arg2)
        else:
            res.amount = parse_amount(arg1)
        return res

    # Attempt to parse a normal bet.
    amount = parse_amount(arg1)
    if amount >= 0:
        res.amount = amount
        res.side = arg2
        return res

    amount = parse_amount(arg2)
    if amount >= 0:
        res.amount = amount
        res.side = arg1
        return res

    return res


class User(commands.Cog):
    """Basic user commands.

    Betting Guideline:
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
    @commands.command(name="leaderboard", aliases=("board", 'lb'))
    async def leaderboard(self, ctx: commands.Context,
                          category: str = param(description="Board to display.",
                                                default='exp')) -> None:
        """Shows the current leaderboard. Optional type of board.
        Valid optional boards are:
        gold, exp, deaths, kills, level, difficulty, gold_multiplier, msg_count


        examples:
            (prefix)leaderboard
            (prefix)leaderboard gold
        """
        if not ctx.guild:
            return

        category = category.lower()
        if category not in ('gold', 'exp', 'deaths', 'kills', 'msg_count',
                            'level', 'difficulty', 'gold_multiplier'):
            await ctx.send("That is not a valid leaderboard.", delete_after=30)
            return

        all_users = users.Manager.getall()
        all_users = list(filter(lambda u: getattr(u, category) > 0, all_users))
        all_users.sort(key=lambda u: getattr(u, category), reverse=True)

        cat_fancy = category.replace('_', ' ').title()

        pos: int = 0
        board: list[str] = []
        kills: int = 0
        for user_l in all_users:
            kills += user_l.kills
            if pos >= 10:
                continue

            # Get the API version of the user.
            user = await get_member(self.bot, ctx.guild.id, user_l.id)
            if not user:
                continue

            # Generate the text for the users position.
            pos += 1
            suffix: str = ""
            if category == 'gold' and user_l.gambles > 0:
                suffix = f"[ Win-Rate: {user_l.win_rate():0.2f}% ]"
            elif category == 'exp':
                suffix = f"[ lvl {user_l.level}, kills: {user_l.kills} ]"
            elif category == 'difficulty':
                suffix = f"[ lvl {user_l.level}, exp: {user_l.exp}, "\
                    f"kills: {user_l.kills} ]"
            elif category == 'level':
                suffix = f"[ exp: {user_l.exp} ]"
            elif category == 'gold_multiplier':
                suffix = f"[ gold: {user_l.gold} ]"
            elif category == 'kills':
                suffix = f"[ lvl {user_l.level}, exp: {user_l.exp} ]"

            # Convert to a sensible significant digit.
            value = getattr(user_l, category)
            display = str(value)
            if isinstance(value, float):
                display = f"{value:0.2f}"

            board.append(f"{pos}: **{user}** - "
                         f"{cat_fancy}: {display} "
                         f"{suffix}")

        # Combine all of the user data into a single message.
        summary = "\n".join(board)
        color = discord.Colour.from_str("#00ff08")
        embed = discord.Embed(title=f"Top 10 {cat_fancy}",
                              description=summary, color=color)
        embed.set_footer(text=f"Total kills: {kills}")
        await ctx.send(embed=embed)

    @commands.command(name="locations", aliases=("location", "loc", "recall"))
    async def locations(self, ctx: commands.Context,
                        location: str = param(
                            description="Optional location to move to",
                            default='none')):
        """Shows your current location, by typing a location it will teleport
        you there.

        examples:
            (prefix)locations
            (prefix)locations Sewers
        """
        user = ctx.author

        # Get the local user.
        user_l = users.Manager.get(user.id)
        c_location: str = 'Unknown'
        if user_l.c_location.name:
            c_location = user_l.c_location.name.title()
        new_loc_text: str = ""

        if location != 'none':
            # Change location.
            if not user_l.change_location(location):
                embed = discord.Embed()
                embed.color = discord.Colour.from_str("#ff0f08")
                embed.description = "Sorry, you have not discovered that "\
                    "location yet."
                embed.set_footer(text=f"Current Location: {c_location}")
                return await ctx.send(embed=embed)
            new_loc_text = "`Location updated!`\n\n"
            if user_l.c_location.name:
                c_location = user_l.c_location.name.title()
            user_l.save()

        # Build list of discovered locations.
        loc_text: list[str] = []
        locations = user_l.locations.get_unlocks()
        for n, loc in enumerate(locations):
            lfeed = '???' if n + 1 == len(locations) else '???'
            current = ""
            if loc == c_location.lower():
                current = " (Current)"
            loc_text.append(f"> {lfeed} {loc.title()}{current}")
        full_text = '\n'.join(loc_text)

        # Get the list of connections.
        conn_text: list[str] = []
        conns = user_l.locations.connections(user_l.c_location)
        for n, loc in enumerate(conns):
            lfeed = '???' if n + 1 == len(conns) else '???'
            name = "Unknown"
            if loc.name:
                name = loc.name.title()
            conn_text.append(f"> {lfeed} {name}")
        conn_full = '\n'.join(conn_text)

        color = discord.Colour.from_str("#00ff08")
        desc = f"**{user}**\n\n{new_loc_text}"\
            f"**id**: {user.id}\n"\
            f"**level**: {user_l.level}\n"\
            f"**messages**: {user_l.msg_count}\n\n"\
            "> __**Areas Unlocked**__:\n"\
            f"**{full_text}**\n\n"\
            "> __**Area Connections**__:\n"\
            f"**{conn_full}**\n"

        embed = discord.Embed(description=desc, color=color)
        embed.set_footer(text=f"Current Location: {c_location}")
        embed.set_thumbnail(url=user.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name="stats", aliases=("balance", "who", "whois"))
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
        category = Destructable.Category.OTHER
        await DestructableManager.remove_many(ctx.author.id, True, category)

        # Check if the channel name is a user id
        thread = ctx.message.channel
        if isinstance(thread, discord.Thread):
            # Try to get the user.
            user_id: int = 0
            try:
                user_id = int(thread.name)
            except BaseException:
                pass
            thread_user = await get_user(self.bot, user_id)
            if thread_user:
                user = thread_user

        view = UserView(self.bot)
        view.set_user(user)
        embed = UserView.get_panel(user)
        message = await ctx.send(embed=embed, view=view)

        # Create the destructable.
        destruct = Destructable(category, ctx.author.id, 60, True)
        destruct.set_message(message)

    @commands.is_owner()
    @commands.command(name="spawn")
    async def spawn(self, ctx: commands.Context,
                    to: discord.Member = param(description="Recipient"),
                    amount: int = param(description="Amount to spawn.")) -> None:
        """Give or remove gold from a user.
        example:
            (prefix)spawn @Gatekeeper 40
        """
        # Remove all 'DOUBLE OR NOTHING' buttons. Prevents gold duping.
        category = Destructable.Category.GAMBLE
        await DestructableManager.remove_many(to.id, True, category)

        # Give the gold to the user and save them.
        user = users.Manager.get(to.id)
        user.gold += amount
        user.save()

        # Create the transaction text.
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
                   to: discord.Member = param(description="Recipient"),
                   amount: int = param(description="Amount to give.")) -> None:
        """Give gold from yourself to another user.
        example:
            (prefix)give @Gatekeeper 40
        """
        from_user = users.Manager.get(ctx.author.id)
        if amount > from_user.gold:
            amount = from_user.gold

        if amount <= 0:
            await ctx.send(f"{amount}gp is not a valid gold amount to send.")
            return

        # Prevent giving gold to self.
        to_user = users.Manager.get(to.id)
        if from_user.id == to_user.id:
            msg = "What would be the purpose in sending gold to yourself?"
            await ctx.send(msg)
            return

        # Remove all 'DOUBLE OR NOTHING' buttons. Prevents gold duping.
        category = Destructable.Category.GAMBLE
        await DestructableManager.remove_many(to_user.id, True, category)
        await DestructableManager.remove_many(from_user.id, True, category)

        # Remove from the giver and add to the receiver.
        from_user.gold -= amount
        to_user.gold += amount

        # Save both users involved.
        from_user.save()
        to_user.save()

        # Create the transaction text.
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
                  amount: str = param(description="Amount to bet. 20gp min."),
                  side: str = param(description="High, low, or seven")):
        """Place your bet, requires an amount and position (high, low, seven)
        The amount required is either 20gp OR 10% of your current gold.

        Check your current gold with: (prefix)stats
        example:
            (prefix)bet 40 low
        """
        if not ctx.guild or not isinstance(ctx.author, discord.Member):
            await ctx.reply("You must be in a server to do that.",
                            delete_after=30)
            return

        # Attempt to convert the passed parameters to real values.
        user_bet = extract_bet(amount, side)

        view = None
        color_hex = "#ff0f08"  # Loss color.
        user = users.Manager.get(ctx.author.id)

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

        # Remove all 'DOUBLE OR NOTHING' buttons assigned to the user.
        category = Destructable.Category.GAMBLE
        await DestructableManager.remove_many(user.id, True, category)

        # Start the gambling process.
        old_gold = user.gold
        results = gamble(user, str(ctx.author), user_bet)
        if results.iserror:
            color = discord.Colour.from_str(color_hex)
            embed = discord.Embed(description=results.msg, color=color)
            return await ctx.send(embed=embed, delete_after=60)

        # Update their stats.
        user.save()
        gold_dropped: int = 0
        if results.winnings > 0:
            user_bet.amount = results.winnings
            # Prepare to present them with a 'DOUBLE OR NOTHING' opportunity.
            view = GambleView(self.bot, user, 300, user_bet, old_gold)
            color_hex = "#00ff08"
        elif random.randint(1, 12) == 1 and user.gold < user.minimum(20):
            # Dealer gives some gold.
            low = user.minimum(20)
            gold_dropped = random.randrange(int(low * 0.8), int(low * 1.2))
            user.gold += gold_dropped
            user.save()

        # Update the bot statistics.
        if self.bot.user:
            bot_user = users.Manager.get(self.bot.user.id)
            bot_user.gambles += 1
            if results.winnings == 0:
                bot_user.gambles_won += 1
            bot_user.save()

        color = discord.Colour.from_str(color_hex)
        embed = discord.Embed(description=results.msg, color=color)
        embed.set_footer(text=f"Next minimum: {user.minimum(20)} gp")

        # Spawn the message and create a destructable for it.
        msg = await ctx.send(embed=embed, view=view)
        if view and msg:
            category = Destructable.Category.GAMBLE
            destruct = Destructable(category, user.id, 300)
            destruct.set_message(message=msg)

        if gold_dropped > 0:
            # Dealer gives some gold.
            embed = discord.Embed(color=discord.Colour.from_str("#f1c800"))
            dealer: str = "A voice"
            if self.bot.user:
                dealer = str(self.bot.user)
            embed.description = f'**{dealer}** whispers:\n"Down on your luck?'\
                f' Here is **{gold_dropped}** gp to keep your spirits up."'
            await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.has_guild_permissions(manage_messages=True)
    @commands.command(name="lotto", aliases=("raffle",))
    async def lotto(self, ctx: commands.Context,
                    amount: int = param(description="Amount of winners."),
                    ) -> None:
        """Performs the lotto assigning all users with the defined lotto role
        a new winner lotto role. Can take serveral seconds to process.

        Limit: 20

        example:
            (prefix)lotto 20
        """
        guild = ctx.guild
        if not guild:
            return

        if amount <= 0:
            await ctx.send("Need more than 0 winners picked.")
            return

        amount = min(amount, 20)
        setting = settings.Manager.get(guild.id)

        # Get the role that lotto members belong to.
        lotto_role = guild.get_role(setting.lotto_role_id)
        if not lotto_role:
            await ctx.send("Lotto role could not be found.")
            return

        # Get the role to assign to all winners of the lott.
        winner_role = guild.get_role(setting.lotto_winner_role_id)
        if not winner_role:
            await ctx.send("Winner role could not be found.")
            return

        await ctx.send("__**Lotto started!**__\n... **drum roll** ...")

        # Perform Lotto.
        lotto_pool: list[discord.Member] = []
        for member in lotto_role.members:
            if member in winner_role.members:
                # Prevent double winners.
                continue
            if winner_role in member.roles:
                # Prevent previous winners.
                continue
            lotto_pool.append(member)

        winners: list[discord.Member] = []
        if amount >= len(lotto_pool):
            # Give all users in lotto pool the role if the request was too many
            winners = lotto_pool
        else:
            while len(winners) < amount:
                if len(lotto_pool) == 0:
                    break

                # Pick a random position within the list of users.
                pos = random.randrange(0, len(lotto_pool))
                user = lotto_pool[pos]
                if not user:
                    continue

                # Assign them as a winner if they have not already won.
                if winner_role not in user.roles and user not in winners:
                    winners.append(user)

                # Remove the user from the pool.
                lotto_pool = [u for u in lotto_pool if u.id != user.id]

        title = "__**Lotto Winners!**__"
        if len(winners) == 0:
            await ctx.send(f"{title}\n> ??? No Winners.")
            return

        # Assign the winner role to all winners..
        winner_text: list[str] = []
        for n, winner in enumerate(winners):
            lfeed = '???' if n + 1 == len(winners) else '???'
            winner_text.append(f"> {lfeed} {winner.mention} (**{winner}**)")

            # Remove the lotto role and add winning role.
            roles = [r for r in winner.roles if r != lotto_role]
            roles.append(winner_role)
            try:
                await winner.edit(roles=roles)
            except BaseException:
                pass

        full_text = '\n'.join(winner_text)
        # Format and print winners.
        msg = await ctx.send(f"{title}\n{full_text}\n\n"
                             f"Congratulations on your new role: **{winner_role}**")
        if not msg:
            return

        # Send an embed to all winners.
        embed = discord.Embed(title="Your ticket won!")
        embed.color = discord.Colour.from_str("#00ff08")
        embed.description = "You had a winning lotto/raffle ticket on "\
            f"**{guild.name}**!\nYour reward is the "\
            f"**{winner_role}** role.\n\nClick the link to access the "\
            f"announcement: [**Lotto Results**]({msg.jump_url})"
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        # Notify the winners.
        for winner in winners:
            try:
                view = DMDeleteView(ctx.bot)
                await winner.send(embed=embed, view=view)
            except BaseException:
                pass


async def setup(bot: DiscordBot) -> None:
    """This is called by process that loads extensions."""
    await bot.add_cog(User(bot))
