import random
from typing import Optional

import discord
from discord import ui

from dclient import DiscordBot, DestructableView
from managers import users

valid_input = ("high", "low", "seven", "7")


class GambleResult():
    def __init__(self, msg: str, iserror: bool) -> None:
        self.msg = msg
        self.iserror = iserror
        self.winnings = 0


def roll_dice() -> tuple[int, int]:
    return (random.randint(1, 6), random.randint(1, 6))


def gamble(user: users.User, name: str,
           amount: int, side: str, loss_reset: int = 0,
           min_override: int = -1, mod: int = 1) -> GambleResult:
    if amount <= 0:
        return GambleResult("cannot be 0 or less.", True)

    if side.lower() not in valid_input:
        return GambleResult("You must choose: high, low, or seven", True)

    if amount > user.gold:
        amount = user.gold

    old_min = user.minimum(20)
    if min_override >= 0:
        old_min = min_override
    if amount < old_min:
        return GambleResult(f"You must reach the minimum bet of {old_min} gp!\n"
                            f"Current holdings: {user.gold} gp.", True)

    dice = roll_dice()
    total = dice[0] + dice[1]

    winnings: int = 0
    res_status: str = "high"
    if total < 7:
        res_status = "low"
    elif total == 7:
        res_status = "seven"

    if side.lower() == "high" and total > 7:
        winnings = amount * mod
    if side.lower() == "low" and total < 7:
        winnings = amount * mod
    if side.lower() in ("seven", "7") and total == 7:
        winnings = amount * 4 * mod

    change = -1 * amount
    old_holding = user.gold
    res = f"You **lost** {amount} gp"
    if winnings > 0:
        user.gambles_won += 1
        change = winnings
        res = f"You **won** {winnings} gp"

    user.gold += change
    if winnings == 0 and loss_reset > 0:
        res = "You **lost**, breaking even"
        user.gold = loss_reset
    user.gambles += 1

    res = GambleResult(f"**Holdings**: {old_holding} gp\n"
                       f"**Minimum**: {old_min} gp\n"
                       f"**Gamble**: {amount} gp\n"
                       f"**Position**: {side.lower()}\n\n"
                       f" > ❊**{name}** rolls {dice[0]}, {dice[1]}❊\n\n"
                       f"**Result**: {total}, and {res_status}\n"
                       f"{res}. Current holdings: {user.gold} gp.",
                       False)
    res.winnings = winnings
    return res


class GambleView(ui.View):
    def __init__(self, bot: DiscordBot,
                 user: users.User,
                 decay: int, amount: int, side: str, base: int) -> None:
        self.bot = bot
        self.user = user
        self.amount = amount
        self.side = side
        self.base = base
        self.decay = decay

        super().__init__(timeout=decay * 2)

    @ui.button(label='DOUBLE OR NOTHING', style=discord.ButtonStyle.red,
               custom_id='gamble_view:double')
    async def gamble(self, interaction: discord.Interaction, button: ui.Button):
        res = interaction.response
        if interaction.user.id != self.user.id:
            return await res.send_message("You were not the original gambler.",
                                          ephemeral=True)
        channel = interaction.channel
        if not channel or not isinstance(channel, discord.TextChannel):
            return
        await self.bot.rm_user_destructable(self.user.id)

        view = None
        color_hex = "#ff0f08"  # Loss color.
        results = gamble(self.user, str(interaction.user),
                         self.amount, self.side, self.base, self.amount, 2)
        if results.iserror:
            color = discord.Colour.from_str(color_hex)
            embed = discord.Embed(description=results.msg, color=color)
            return await res.send_message(embed=embed, ephemeral=True)

        if results.winnings > 0:
            view = GambleView(self.bot, self.user, self.decay,
                              results.winnings, self.side, self.base)
            color_hex = "#00ff08"

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
        msg: Optional[discord.Message] = None
        if not view:
            return await channel.send(embed=embed)
        # Schedule to delete the view.
        msg = await channel.send(embed=embed, view=view)
        if msg:
            destructable = DestructableView(msg, self.user.id, 300)
            self.bot.add_destructable(destructable)
