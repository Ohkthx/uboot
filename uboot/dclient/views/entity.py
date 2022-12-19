"""Views / Panels for various entities that can spawn."""
import random

import discord
from discord import ui

from dclient.destructable import DestructableManager
from managers import users, entities

# Flavour winning text.
win_text: list[str] = ["slays", "defeats", "conquers", "strikes down", "kills",
                       "obliterates", "slaps them with a wet fish killing",
                       ]


def attack(user: discord.Member, entity: entities.Entity) -> str:
    """Attempts to attack the entity."""
    user_l = users.Manager.get(user.id)
    if user_l.gold < entity.health:
        return f"**{user}** does not have enough gold to fight "\
            f"**{entity.name}**!\nForced to flee like a coward."

    exp = user_l.expected_exp(entity.health)
    user_l.gold -= entity.health
    user_l.kills += 1
    user_l.exp += exp
    user_l.save()

    win = win_text[random.randrange(0, len(win_text))]
    return f"**{user}** {win} **{entity.name}**!\n"\
        f"**Reward**: {exp:0.2f} exp\n"


class Dropdown(ui.Select):
    """Actions that can be performed against the entity."""

    def __init__(self, user: discord.Member, entity: entities.Entity):
        self.user = user
        self.entity = entity
        options = [
            discord.SelectOption(
                label='Attack', description="Choose to attack."),
            discord.SelectOption(
                label='Flee', description="Choose to run."),
        ]
        super().__init__(options=options, custom_id="entity_view:dropdown")

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
            print("Message cache failed on entity spawning.")
            return

        cached = msg.reference.cached_message

        embed = discord.Embed()
        embed.color = discord.Colour.from_str("#ff0f08")
        embed.description = f"**{self.user}** flees like a coward from "\
            f"**{self.entity.name}**, keeping their gold."

        if self.values[0].lower() == 'attack':
            embed.color = discord.Colour.from_str("#00ff08")
            if user_l.gold < self.entity.health:
                embed.color = discord.Colour.from_str("#ff0f08")
            embed.description = attack(self.user, self.entity)
            embed.set_footer(text=f"Current gold: {user_l.gold} gp")
        elif self.values[0].lower() == 'flee':
            pass
        else:
            embed.color = discord.Colour.from_str("#F1C800")
            embed.description = "You perform some unknown action?! What a feat."

        # Delete the old destructable.
        await DestructableManager.remove_one(msg.id, True)
        await cached.reply(embed=embed)


class EntityView(ui.View):
    """Entity View that can be interacted with after reboots."""

    def get_panel(self) -> discord.Embed:
        """Produces the entities message."""
        user_l = users.Manager.get(self.user.id)
        embed = discord.Embed()

        action = self.entity.get_action()
        cost = self.entity.health
        gained_exp = user_l.expected_exp(cost)

        loc_name = 'Unknown'
        if self.entity.location.name:
            loc_name = self.entity.location.name.title()
        embed.color = discord.Colour.from_str("#F1C800")
        embed.description = f"**{self.user}** {action} by **{self.entity.name}**!\n"\
            f"**Location**: {loc_name}\n"\
            f"**Health**: {cost}\n\n"\
            "> __**Options**:__\n"\
            f"> ├ **Attack**: Costing {cost} gp, gaining {gained_exp:0.2f} exp.\n"\
            "> └ **Flee**: Flee, keeping your gold.\n\n"\
            "Only the user who spawned the creature can take action."
        embed.set_footer(text=f"Current gold: {user_l.gold} gp")

        return embed

    def __init__(self, user: discord.Member, entity: entities.Entity):
        self.user = user
        self.entity = entity
        super().__init__(timeout=None)
        self.add_item(Dropdown(user, entity))
