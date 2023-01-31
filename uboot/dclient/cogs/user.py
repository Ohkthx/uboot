"""Various commands that support the gambling mechanic."""
import random
from datetime import datetime, timedelta
from typing import Optional

import discord
from discord.ext import commands
from discord.ext.commands import param

from managers import users, settings, react_roles, entities
from managers.locations import Locations, Area, Floor, Level
from managers.logs import Log
from dclient import DiscordBot
from dclient.destructable import DestructableManager, Destructable
from dclient.views.gamble import GambleView, gamble, ExtractedBet
from dclient.views.dm import DMDeleteView
from dclient.views.user import (TradeView, UserStatsView, InventoryView,
                                LocationView)
from dclient.helper import (get_member, get_message,
                            get_role, get_user, check_minigame)


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

    @commands.command(name="taunt")
    async def taunt(self, ctx: commands.Context) -> None:
        """Attempt to taunt a nearby creature to attack you.

        example:
            (prefix}taunt
        """
        if not ctx.guild or not isinstance(ctx.author, discord.Member):
            return

        # Check that the user has the minigame role.
        passed, msg = await check_minigame(self.bot, ctx.author, ctx.guild.id)
        if not passed:
            await ctx.reply(msg, delete_after=30)
            return

        # Prevent taunt spam.
        user_l = users.Manager.get(ctx.author.id)
        if not user_l.timer_expired(users.Cooldown.TAUNT):
            timediff = datetime.now() - user_l.cooldown(users.Cooldown.TAUNT)
            minutes = (timedelta(minutes=12) - timediff) / timedelta(minutes=1)
            await ctx.reply("You are tired and cannot taunt for another "
                            f"{minutes:0.1f} minutes.",
                            delete_after=30)
            return

        # Check if the user is in combat.
        if user_l.incombat:
            await ctx.reply("You are already in combat with another creature.",
                            delete_after=30)
            return

        # Update with a new taunt attempt.
        user_l.mark_cooldown(users.Cooldown.TAUNT)

        # Spawn the creature.
        loc = user_l.c_location
        floor = user_l.c_floor
        difficulty = user_l.difficulty
        inpowerhour = self.bot.powerhours.get(ctx.guild.id)
        entity = entities.Manager.check_spawn(loc, floor, difficulty,
                                              inpowerhour is not None,
                                              user_l.ispowerhour,
                                              True)
        if not entity:
            await ctx.reply("No nearby enemies react to your taunt.",
                            delete_after=30)
            return

        await self.bot.add_entity(ctx.message, ctx.author, entity)

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
        if not ctx.guild or not isinstance(user, discord.Member):
            return

        # Check that the user has the minigame role.
        passed, msg = await check_minigame(self.bot, user, ctx.guild.id)
        if not passed:
            await ctx.reply(msg, delete_after=30)
            return

        # Get the local user.
        user_l = users.Manager.get(user.id)
        c_location: str = 'Unknown'
        if user_l.c_location.name:
            c_location = user_l.c_location.name.title()
        new_loc_text: str = ""

        area: Optional[Area] = Locations.parse_area(location)
        if location != 'none' and area:
            # Change location.
            new_loc: Optional[Floor] = user_l.change_location(area, Level.ONE)
            if not new_loc:
                embed = discord.Embed()
                embed.color = discord.Colour.from_str("#ff0f08")
                embed.description = "Sorry, you have not discovered that "\
                    "location yet."
                embed.set_footer(text=f"Current Location: {c_location}")
                return await ctx.send(embed=embed)
            new_loc_text = "`Location updated!`\n\n"
            user_l.save()
            await ctx.reply(new_loc_text, delete_after=60)

        view = LocationView(self.bot)
        view.set_user(user)

        embed = LocationView.get_panel(user)
        await ctx.send(embed=embed, view=view)

    @commands.command(name="bank", aliases=("items", "balance", "withdraw"))
    async def bank(self, ctx: commands.Context,
                   user: discord.User = param(
                       description="Optional Id of the user to lookup.",
                       default=lambda ctx: ctx.author,
                       displayed_default="self")):
        """Shows the users bank and stored items with an option to sell.
        Defaults to the user who performed the command.

        examples:
            (prefix)bank
            (prefix)bank @Gatekeeper
            (prefix)bank 1044706648964472902
        """
        if not ctx.guild or not isinstance(ctx.author, discord.Member):
            return

        # Check that the user has the minigame role.
        passed, msg = await check_minigame(self.bot, ctx.author, ctx.guild.id)
        if not passed:
            await ctx.reply(msg, delete_after=30)
            return

        category = Destructable.Category.OTHER
        await DestructableManager.remove_many(ctx.author.id, True, category)

        user_l = users.Manager.get(user.id)

        view = InventoryView(self.bot)
        view.set_user(user, user_l.bank)

        embed = InventoryView.get_panel(user, user_l.bank)
        message = await ctx.send(embed=embed, view=view)

        # Create the destructable.
        destruct = Destructable(category, ctx.author.id, 60, True)
        destruct.set_message(message)

    @commands.command(name="stats", aliases=("who", "whois"))
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
        if not ctx.guild or not isinstance(ctx.author, discord.Member):
            return

        # Check that the user has the minigame role.
        passed, msg = await check_minigame(self.bot, ctx.author, ctx.guild.id)
        if not passed:
            await ctx.reply(msg, delete_after=30)
            return

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

        view = UserStatsView(self.bot)
        view.set_user(user)
        embed = UserStatsView.get_panel(user)
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
    @commands.group(name="give", aliases=("trade",))
    async def give(self, ctx: commands.Context) -> None:
        """Give another player either gold or items.

        examples:
            (prefix)give gold @Gatekeeper 100
            (prefix)give item @Gatekeeper
        """
        if not ctx.invoked_subcommand:
            await ctx.send('invalid give command.')

    @give.command(name="gold", aliases=("gp",))
    async def give_gold(self, ctx: commands.Context,
                        to: discord.Member = param(description="Recipient"),
                        amount: int = param(description="Amount to give.")) -> None:
        """Give gold from yourself to another user.
        example:
            (prefix)give gold @Gatekeeper 40
        """
        if not ctx.guild or not isinstance(ctx.author, discord.Member):
            return

        # Check that the user has the minigame role.
        passed, msg = await check_minigame(self.bot, ctx.author, ctx.guild.id)
        if not passed:
            await ctx.reply(msg, delete_after=30)
            return

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

    @give.command(name="item", aliases=("items",))
    async def give_item(self, ctx: commands.Context,
                        to: discord.Member = param(description="Recipient"),
                        ) -> None:
        """Give an item from yourself to another user.
        example:
            (prefix)give item @Gatekeeper
        """
        if not ctx.guild or not isinstance(ctx.author, discord.Member):
            return

        # Check that the user has the minigame role.
        passed, msg = await check_minigame(self.bot, ctx.author, ctx.guild.id)
        if not passed:
            await ctx.reply(msg, delete_after=30)
            return

        from_user = users.Manager.get(ctx.author.id)

        # Prevent giving items to self.
        to_user = users.Manager.get(to.id)
        if from_user.id == to_user.id:
            msg = "What would be the purpose in sending an item to yourself?"
            await ctx.send(msg)
            return

        # Remove all buttons. Prevents item duping.
        category = Destructable.Category.OTHER
        await DestructableManager.remove_many(from_user.id, True, category)

        # Get the 'give' view.
        view = TradeView(self.bot)
        view.set_user(ctx.author)

        # Reuse the bank / item panel, modify the user ids on the bottom.
        embed = InventoryView.get_panel(ctx.author, from_user.bank)
        embed.set_footer(text=f"{from_user.id}:{to_user.id}")
        await ctx.send(embed=embed, view=view)

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
        passed, msg = await check_minigame(self.bot, ctx.author, ctx.guild.id)
        if not passed:
            await ctx.reply(msg, delete_after=30)
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
        lotto_role = guild.get_role(setting.lotto.role_id)
        if not lotto_role:
            await ctx.send("Lotto role could not be found.")
            return

        # Get the role to assign to all winners of the lott.
        winner_role = guild.get_role(setting.lotto.winner_role_id)
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
            await ctx.send(f"{title}\n> └ No Winners.")
            return

        # Assign the winner role to all winners..
        winner_text: list[str] = []
        for n, winner in enumerate(winners):
            lfeed = '└' if n + 1 == len(winners) else '├'
            winner_text.append(f"> {lfeed} {winner.mention} (**{winner}**)")

            # Remove the lotto role and add winning role.
            roles = [r for r in winner.roles if r != lotto_role]
            roles.append(winner_role)
            try:
                await winner.edit(roles=roles)
            except BaseException as exc:
                Log.error(f"Could not add {winner} to winning role.\n{exc}",
                          guild_id=guild.id, user_id=winner.id)

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
            except BaseException as exc:
                Log.error(f"Could not notify {winner} via DM of lotto win.\n"
                          f"{exc}",
                          guild_id=guild.id, user_id=winner.id)

    @commands.guild_only()
    @commands.has_guild_permissions(manage_messages=True)
    @commands.command(name="lotto-verify", aliases=("lverify",))
    async def lotto_verify(self, ctx: commands.Context) -> None:
        """Verifies the lotto participants, notifies if a user has reacted but
        has not won nor has the lotto participant role.

        example:
            (prefix)lotto-verify
        """
        guild = ctx.guild
        if not guild:
            return

        # Get the settings for the server.
        setting = settings.Manager.get(guild.id)
        lotto_id = setting.lotto.role_id
        winner_id = setting.lotto.winner_role_id

        if lotto_id <= 0:
            await ctx.send("lotto role is unset, please set it "
                           "with settings command.")

        if winner_id <= 0:
            await ctx.send("winner role is unset, please set it "
                           "with settings command.")

        # Get the roles involved in the lotto.
        lotto_role = await get_role(self.bot, guild.id, lotto_id)
        if not lotto_role:
            await ctx.send("lotto role no longer exists it appears.",
                           delete_after=15)
            return

        winner_role = await get_role(self.bot, guild.id, winner_id)
        if not winner_role:
            await ctx.send("winner role no longer exists it appears.",
                           delete_after=15)
            return

        # Get the list of opt-in users.
        channel_id = setting.reactrole.channel_id
        msg_id = setting.reactrole.msg_id
        react_msg = await get_message(self.bot, channel_id, msg_id)
        if not react_msg:
            await ctx.send("could not identify the reaction-role message.")
            return

        # Get the reaction from the message.
        react_role = react_roles.Manager.get(lotto_role.id)
        if not react_role:
            await ctx.send("could not get reaction-role pair, reaction."
                           "may be currently unset.",
                           delete_after=15)
            return

        emoji = react_role.reaction
        reactions = react_msg.reactions
        reaction = next((x for x in reactions if x.emoji == emoji), None)
        if not reaction:
            await ctx.send("reaction could not be found.", delete_after=15)
            return

        # Check those who are missing the role but should have it.
        missing_role: list[str] = []
        all_users: list[discord.Member] = []
        async for user in reaction.users():
            if user.bot or not isinstance(user, discord.Member):
                continue
            all_users.append(user)

            # Check roles.
            if not user.get_role(lotto_id) and not user.get_role(winner_id):
                missing_role.append(f"> **{user}** ({user.id})")

        # Build the text.
        total_missing = "> none"
        if len(missing_role) > 0:
            total_missing = '\n'.join(missing_role)

        embed = discord.Embed(title="Lotto Verification")
        embed.color = discord.Colour.blurple()
        embed.set_footer(text="Output above are potential errors.")
        embed.description = f"**Users who reacted**: {len(all_users)}\n"\
            f"**Users in lotto**: {len(lotto_role.members)}\n\n"\
            "__**Has reacted, no roles**__:\n"\
            f"{total_missing}"
        await ctx.send(embed=embed)


async def setup(bot: DiscordBot) -> None:
    """This is called by process that loads extensions."""
    await bot.add_cog(User(bot))
