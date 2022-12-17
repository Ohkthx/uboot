"""Views / Panels for various monsters that can spawn."""
import random

import discord
from discord import ui

from managers import users, monsters

# Flavour winning text.
win_text: list[str] = ["slays", "defeats", "conquers", "strikes down", "kills",
                       "obliterates", "slaps them with a wet fish killing",
                       ]


def attack(user: discord.Member, monster: monsters.Monster) -> str:
    """Attempts to attack the monster."""
    user_l = users.Manager.get(user.id)
    if user_l.gold < monster.health:
        return f"**{user}** does not have enough gold to fight "\
            f"**{monster.name}**!\nThey are forced to flee like a coward."

    exp = user_l.expected_exp(monster.health)
    user_l.gold -= monster.health
    user_l.kills += 1
    user_l.exp += exp
    user_l.save()

    win = win_text[random.randrange(0, len(win_text))]
    return f"**{user}** {win} **{monster.name}**!\n"\
        f"**Reward**: {exp} exp\n"


class Dropdown(ui.Select):
    """Actions that can be performed against the monster."""

    def __init__(self, user: discord.Member, monster: monsters.Monster):
        self.user = user
        self.monster = monster
        options = [
            discord.SelectOption(
                label='Attack', description="Choose to attack."),
            discord.SelectOption(
                label='Flee', description="Choose to run."),
        ]
        super().__init__(options=options, custom_id="monster_view:dropdown")

    async def callback(self, interaction: discord.Interaction):
        """Prompts the user to select and option."""
        res = interaction.response
        msg = interaction.message

        user_l = users.Manager.get(self.user.id)
        if interaction.user != self.user:
            await res.send_message("You are not in combat with that creature.",
                                   ephemeral=True,
                                   delete_after=30)
            return

        if not msg or not msg.reference or not msg.reference.cached_message:
            print("Message cache failed on monster spawning.")
            return

        cached = msg.reference.cached_message

        embed = discord.Embed()
        embed.color = discord.Colour.from_str("#ff0f08")
        embed.description = f"**{self.user}** flees like a coward from "\
            f"**{self.monster.name}**, keeping their gold."

        if self.values[0].lower() == 'attack':
            embed.color = discord.Colour.from_str("#00ff08")
            if user_l.gold < self.monster.health:
                embed.color = discord.Colour.from_str("#ff0f08")
            embed.description = attack(self.user, self.monster)
            embed.set_footer(text=f"Current gold: {user_l.gold} gp")
        elif self.values[0].lower() == 'flee':
            pass
        else:
            embed.color = discord.Colour.from_str("#F1C800")
            embed.description = "You perform some unknown action?! What a feat."

        await msg.delete()
        await cached.reply(embed=embed)


class MonsterView(ui.View):
    """Monster View that can be interacted with after reboots."""

    def get_panel(self) -> discord.Embed:
        """Produces the monsters message."""
        user_l = users.Manager.get(self.user.id)
        embed = discord.Embed()

        action = self.monster.get_action()
        cost = self.monster.health
        gained_exp = user_l.expected_exp(cost)

        embed.color = discord.Colour.from_str("#F1C800")
        embed.description = f"**{self.user}** {action} by **{self.monster.name}**!\n"\
            f"**Health**: {cost}\n\n"\
            "> __**Options**:__\n"\
            f"> ├ **Attack**: Costing {cost} gp but gaining {gained_exp} exp.\n"\
            "> └ **Flee**: Flee, keeping your gold.\n\n"\
            "Only the user who spawned the creature can take action."
        embed.set_footer(text=f"Current gold: {user_l.gold} gp")

        return embed

    def __init__(self, user: discord.Member, monster: monsters.Monster):
        self.user = user
        self.monster = monster
        super().__init__(timeout=None)
        self.add_item(Dropdown(user, monster))
