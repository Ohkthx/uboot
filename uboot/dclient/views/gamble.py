"""Gambling is a mechanic to spend a virtual currency (gold / gold piece) that
is slowly accumulated while users participate in conversation within servers.
"""
import random

import discord
from discord import ui

from dclient.bot import DiscordBot
from dclient.destructible import DestructibleManager, Destructible
from managers import users

# All valid options for the generic betting game.
valid_input = ("high", "low", "seven", "7")


class ExtractedBet:
    """Results of extracting a users bet parameters."""

    def __init__(self, amount: int, side: str,
                 is_all: bool, minimum: bool) -> None:
        self.amount: int = amount
        self.side: str = side
        self.is_all: bool = is_all
        self.minimum: bool = minimum


class GambleResult:
    """Small wrapper for the result of a gamble session."""

    def __init__(self, msg: str, is_error: bool) -> None:
        self.msg = msg
        self.is_error = is_error
        self.winnings = 0


def roll_dice() -> tuple[int, int]:
    """Calculates a 2d6 roll."""
    return random.randint(1, 6), random.randint(1, 6)


def gamble(user: users.User, name: str,
           bet: ExtractedBet, loss_reset: int = 0,
           min_override: int = -1, mod: int = 1) -> GambleResult:
    """Performs the arithmetic and validation for a gambling session."""
    if bet.is_all and min_override < 0:
        # Set the amount to all the users gold if passed.
        bet.amount = user.gold
    elif bet.minimum and min_override < 0:
        # Set the amount to minimum amount.
        bet.amount = user.minimum(20)

    if bet.amount <= 0:
        return GambleResult("cannot be 0 or less.", True)

    if bet.side.lower() not in valid_input:
        return GambleResult("You must choose: high, low, or seven", True)

    # Prevent the user betting more than maximum amount they own.
    if bet.amount > user.gold:
        bet.amount = user.gold

    # Force a minimum to prevent users step gambling, 1, 2, 4, 8, 16, etc.
    old_min = user.minimum(20)
    if min_override >= 0:
        old_min = min_override
    if bet.amount < old_min:
        return GambleResult(f"You must reach the minimum bet of {old_min} gp!\n"
                            f"Current holdings: {user.gold} gp."
                            f" Bet amount: {bet.amount}", True)

    dice = roll_dice()
    total = dice[0] + dice[1]

    # Get the status text.
    winnings: int = 0
    res_status: str = "high"
    if total < 7:
        res_status = "low"
    elif total == 7:
        res_status = "seven"

    # Calculate the winnings if there are some.
    if bet.side.lower() == "high" and total > 7:
        winnings = bet.amount * mod
    if bet.side.lower() == "low" and total < 7:
        winnings = bet.amount * mod
    if bet.side.lower() in ("seven", "7") and total == 7:
        winnings = bet.amount * 4 * mod

    # Update user statistics for wins.
    change = -1 * bet.amount
    old_holding = user.gold
    res = f"You **lost** {bet.amount} gp"
    if winnings > 0:
        user.gambles_won += 1
        change = winnings
        res = f"You **won** {winnings} gp"

    # Apply the change in gold to the user.
    user.gold += change
    if winnings == 0 and loss_reset > 0:
        res = "You **lost**, breaking even"
        user.gold = loss_reset
    user.gambles += 1

    res = GambleResult(f"**Holdings**: {old_holding} gp\n"
                       f"**Minimum**: {old_min} gp\n"
                       f"**Gamble**: {bet.amount} gp\n"
                       f"**Position**: {bet.side.lower()}\n\n"
                       f" > ❊**{name}** rolls {dice[0]}, {dice[1]}❊\n\n"
                       f"**Result**: {total}, and {res_status}\n"
                       f"{res}. Current holdings: {user.gold} gp.",
                       False)
    res.winnings = winnings
    return res


class GambleView(ui.View):
    """Gamble View is presented to the user when they are partaking in
    gambling against the house. If the user wins, they are presented with
    a 'DOUBLE OR NOTHING' button.
    """

    def __init__(self, bot: DiscordBot,
                 user: users.User,
                 decay: int, bet: ExtractedBet, loss_reset: int) -> None:
        self.bot = bot
        self.user = user
        self.bet = bet
        self.loss_reset = loss_reset
        self.decay = decay

        super().__init__(timeout=decay * 2)

    @ui.button(label='DOUBLE OR NOTHING', style=discord.ButtonStyle.red,
               custom_id='gamble_view:double')
    async def gamble(self, interaction: discord.Interaction, _: ui.Button):
        """This button presents itself only when the user has won their
        last gamble. After pressing the button or spawning another, it is
        deleted immediately to prevent exploits.
        """
        # Stop users from pressing the button. Only accessible to the gambler.
        res = interaction.response
        if interaction.user.id != self.user.id:
            return await res.send_message("You were not the original gambler.",
                                          ephemeral=True,
                                          delete_after=60)

        # If somehow spawned outside a text channel, do nothing.
        channel = interaction.channel
        if not channel or not isinstance(channel, discord.TextChannel):
            return

        # Destroy all other buttons assigned to the user to prevent exploits.
        category = Destructible.Category.GAMBLE
        await DestructibleManager.remove_many(self.user.id, True, category)

        view = None
        color_hex = "#ff0f08"  # Loss color.

        # Perform the next gamble.
        results = gamble(self.user, str(interaction.user),
                         self.bet, self.loss_reset, self.bet.amount, 2)
        if results.is_error:
            color = discord.Colour.from_str(color_hex)
            embed = discord.Embed(description=results.msg, color=color)
            return await res.send_message(embed=embed,
                                          ephemeral=True,
                                          delete_after=60)

        # User won again, create another view.
        if results.winnings > 0:
            self.bet.amount = results.winnings
            view = GambleView(self.bot, self.user, self.decay,
                              self.bet, self.loss_reset)
            color_hex = "#00ff08"

        # Save and update the user. Update the bots statistics too.
        self.user.save()
        if self.bot.user:
            bot_user = users.Manager.get(self.bot.user.id)
            bot_user.gambles += 1
            if results.winnings == 0:
                bot_user.gambles_won += 1
            bot_user.save()

        # Create the embed.
        color = discord.Colour.from_str(color_hex)
        text = "`DOUBLE OR NOTHING`"
        embed = discord.Embed(title=text, description=results.msg, color=color)
        embed.set_footer(text=f"Next minimum: {self.user.minimum(20)} gp")

        # Send the embed and/or view.
        if not view:
            return await channel.send(embed=embed)

        # Schedule to delete the view.
        msg = await channel.send(embed=embed, view=view)
        if view and msg:
            category = Destructible.Category.GAMBLE
            destruct = Destructible(category, self.user.id, 300)
            destruct.set_message(message=msg)
