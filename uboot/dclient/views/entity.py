"""Views / Panels for various entities that can spawn."""
import random
from typing import Optional

import discord
from discord import ui

from dclient.destructable import DestructableManager
from managers import users, entities, settings
from managers.loot_tables import Items
from managers.locations import Area

# Flavour winning text.
win_text: list[str] = ["slays", "defeats", "conquers", "strikes down", "kills",
                       "obliterates", "slaps them with a wet fish killing",
                       "murders", "extinguishes the life of",
                       "removes the final sparkle of life from the eyes of",
                       "butchers",
                       ]

ParticipantData = tuple[discord.Member, int, bool]


def attack(participants: list[ParticipantData],
           entity: entities.Entity) -> str:
    """Attempts to attack the entity."""
    if len(participants) == 0:
        return "How did you manage to kill something with no one?"

    leader = users.Manager.get(participants[0][0].id)

    loot = entity.get_loot()
    loot = [l for l in loot if l.type != Items.NONE]

    # Apply all loot to each participant.
    new_area: Optional[Area] = None
    helpers_exp: list[str] = []
    total_exp = leader.expected_exp(entity.max_health)
    for n, helper in enumerate(participants):
        lfeed = '└' if n + 1 == len(participants) else '├'
        user = users.Manager.get(helper[0].id)
        exp = helper[1] / entity.max_health * total_exp
        user.exp += exp
        user.kills += 1
        new_area = user.apply_loot(loot, len(participants) == 1)
        if helper[2] and user.deaths > 0:
            user.deaths = user.deaths - 1
        user.save()
        helpers_exp.append(f"> {lfeed} {helper[0]} gained {exp:0.2f} exp.")
    full_help = '\n'.join(helpers_exp)

    if not new_area:
        loot = [l for l in loot if l.type != Items.LOCATION]

    # Creates the text for loot.
    loot_text: list[str] = []
    for n, item in enumerate(loot):
        lfeed = '└' if n + 1 == len(loot) else '├'
        amt_text: str = ''
        if item.amount > 1:
            amt_text = f" [{item.amount}]"

        name = item.name
        if new_area and item.type == Items.LOCATION:
            # Have special text for new location discoveries.
            area_name = "Unknown"
            if new_area.name:
                area_name = new_area.name.title()
            name = f"NEW AREA FOUND: {area_name}"

        loot_text.append(f"> {lfeed} **{name}**{amt_text}")

    # Combine the text.
    full_loot = '\n'.join(loot_text)
    if len(loot_text) == 0:
        full_loot = "> └ **none**"

    change_loc = ""
    if new_area:
        area_name = "unknown"
        if new_area.name:
            area_name = new_area.name.lower()
        # Notify the user of how to change locations.
        prefix = settings.Manager.prefix
        change_loc = "To recall to a new area, use the "\
            f"`{prefix}recall {area_name}` command"

    win = win_text[random.randrange(0, len(win_text))]
    return f"**{participants[0][0]}** {win} **{entity.name}**!\n\n"\
        f"**Total Reward**: {total_exp:0.2f} exp\n"\
        f"__**Participant Exp**__:\n{full_help}\n\n"\
        f"> __**Loot**__:\n  {full_loot}\n\n"\
        f"{change_loc}"


class Dropdown(ui.Select):
    """Actions that can be performed against the entity."""

    def __init__(self, user: discord.Member, entity: entities.Entity):
        self.user = user
        self.user_l = users.Manager.get(user.id)
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
            if self.user_l.gold < self.entity.health:
                # Get help from another user.
                exp = self.user_l.expected_exp(self.entity.health)
                damage = self.user_l.gold
                self.entity.health -= damage
                self.user_l.gold = 0
                self.user_l.save()
                help_view = HelpMeView(self.user, self.entity, exp, damage)
                help_embed = help_view.get_panel()

                # Register the "loss" callback.
                destruct = DestructableManager.get(msg.id)
                if destruct:
                    destruct.set_callback(help_view.loss_callback)
                    destruct.add_time(60)

                await msg.edit(embeds=[help_embed], view=help_view)
                return await res.send_message(f"You deal {damage} damage.",
                                              ephemeral=True, delete_after=30)
            self.user_l.gold -= self.entity.health
            embed.description = attack([(self.user, self.entity.health, False)],
                                       self.entity)
            embed.set_footer(text=f"Current gold: {self.user_l.gold} gp")
        elif self.values[0].lower() == 'flee':
            pass
        else:
            embed.color = discord.Colour.from_str("#F1C800")
            embed.description = "You perform some unknown action?! What a feat."

        # User is exiting combat.
        self.user_l.set_combat(False)

        # Delete the old destructable.
        await DestructableManager.remove_one(msg.id, True)
        await cached.reply(embed=embed)


class HelpMeView(ui.View):
    """Presents the help information to other players."""

    def __init__(self, user: discord.Member,
                 entity: entities.Entity,
                 exp_gain: float,
                 damage: int):
        self.user = user
        self.user_l = users.Manager.get(self.user.id)
        self.entity = entity
        self.helpers: list[ParticipantData] = [(user, damage, True)]
        self.exp_gain: float = exp_gain
        self.iscomplete: bool = False
        super().__init__(timeout=None)

    def has_contributed(self, user: discord.Member) -> bool:
        """Checks if a user has contributed already."""
        for helper in self.helpers:
            if helper[0] == user:
                return True
        return False

    def get_panel(self) -> discord.Embed:
        """Produces the entities message."""
        embed = discord.Embed(title="REQUESTING HELP!")

        action = self.entity.get_action()
        cost = self.entity.health

        # Add all of the participants and their contributions.
        participants_full: str = ""
        all_help: list[str] = []
        if len(self.helpers) > 0:
            for helper in self.helpers:
                all_help.append(
                    f"> **{helper[0]}** performed {helper[1]} damage.")

            full_help = '\n  '.join(all_help)
            participants_full = f"__**Participants**__:\n{full_help}\n\n"

        loc_name = 'Unknown'
        if self.entity.location.name:
            loc_name = self.entity.location.name.title()

        embed.color = discord.Colour.from_str("#F1C800")
        embed.description = f"**{self.user}** {action} by **{self.entity.name}**!\n"\
            f"**Location**: {loc_name}\n"\
            f"**Health Remaining**: {cost}\n\n"\
            f"{participants_full}"\
            "> __**Options**:__\n"\
            f"> ├ **Help**: Costing {cost} gp, gaining {self.exp_gain:0.2f} exp.\n"\
            "> └ **Do Nothing**: Watch them die.\n\n"
        other_than = f"other than {self.user}"
        embed.set_footer(text=f"Note: Only other users {other_than} can help."
                         "\nYou are risking your gold to help if it is not "
                         "killed.")
        return embed

    async def loss_callback(self, msg: Optional[discord.Message]) -> None:
        """Called when the original message gets deleted."""
        self.user_l.set_combat(False)

        if self.iscomplete:
            return

        if not msg or not msg.reference or not msg.reference.cached_message:
            return

        # Generate all of the gold that was lost text.
        helpers = self.helpers
        dead_text: list[str] = []
        for helper in helpers:
            dead_text.append(f"> {helper[0]} lost {helper[1]} gp.")
        dead_full = '\n'.join(dead_text)

        party = "The **party**" if len(helpers) > 1 else f"**{helpers[0][0]}**"
        description = f"{party} has failed to kill **{self.entity.name}**.\n\n"\
            f"__**Losses**__:\n{dead_full}"

        embed = discord.Embed(description=description)
        embed.color = discord.Colour.from_str("#ff0f08")
        embed.set_footer(text="Better luck next time!")
        cached = msg.reference.cached_message
        await cached.reply(embed=embed)

    @ui.button(label='HELP', style=discord.ButtonStyle.red,
               custom_id='helpme_view:help')
    async def help(self, interaction: discord.Interaction, button: ui.Button):
        """Provides help to a user."""
        res = interaction.response
        msg = interaction.message
        user = interaction.user
        if not isinstance(user, discord.Member):
            return await res.send_message("Could not get your server id.",
                                          ephemeral=True, delete_after=30)

        if self.has_contributed(user):
            return await res.send_message("You have already contributed.",
                                          ephemeral=True,
                                          delete_after=15)

        user_l = users.Manager.get(user.id)
        if user_l.gold == 0:
            return await res.send_message("You do not have any gold.",
                                          ephemeral=True, delete_after=15)

        if not msg or not msg.reference or not msg.reference.cached_message:
            print("Message cache failed on entity spawning.")
            return

        # Cannot do a final blow, so add them as a participant.
        if user_l.gold < self.entity.health:
            DestructableManager.extend(msg.id, 60)
            self.helpers.append((user, user_l.gold, True))
            # Other player helping but cannot finish.
            damage = user_l.gold
            self.entity.health -= damage
            user_l.gold = 0
            user_l.save()
            help_embed = self.get_panel()
            await msg.edit(embeds=[help_embed])
            return await res.send_message(f"You deal {damage} damage.",
                                          ephemeral=True, delete_after=15)

        # Enough gold to do the final blow.
        self.helpers.append((user, self.entity.health, False))
        user_l.gold -= self.entity.health
        self.iscomplete = True
        await res.send_message("You deal the fatal blow!",
                               ephemeral=True, delete_after=30)

        # Build the final embed and send it.
        embed = discord.Embed()
        embed.color = discord.Colour.from_str("#00ff08")
        embed.description = attack(self.helpers, self.entity)
        self.user_l.set_combat(False)

        cached = msg.reference.cached_message
        # Delete the old destructable.
        await DestructableManager.remove_one(msg.id, True)
        await cached.reply(embed=embed)


class EntityView(ui.View):
    """Entity View that can be interacted with after reboots."""

    def __init__(self, user: discord.Member, entity: entities.Entity):
        self.user = user
        self.user_l = users.Manager.get(user.id)
        self.entity = entity
        super().__init__(timeout=None)
        self.add_item(Dropdown(user, entity))

    def get_panel(self) -> discord.Embed:
        """Produces the entities message."""
        user_l = users.Manager.get(self.user.id)
        embed = discord.Embed()

        action = self.entity.get_action()
        cost = self.entity.health
        gained_exp = user_l.expected_exp(cost)

        gold_warning: str = ""
        if user_l.gold < cost:
            gold_warning = "__WARNING__: You do not have enough gold.\n"\
                "By attacking, you risk losing all of it unless someone helps."

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
            f"{gold_warning}"
        embed.set_footer(text=f"Current gold: {user_l.gold} gp")
        return embed

    async def loss_callback(self, msg: Optional[discord.Message]):
        """Cleans up after a loss."""
        self.user_l.set_combat(False)
