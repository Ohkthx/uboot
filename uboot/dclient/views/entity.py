"""Views / Panels for various entities that can spawn."""
import random
from typing import Optional

import discord
from discord import ui

from dclient.helper import get_role
from dclient.destructable import DestructableManager
from managers import users, entities, settings, images
from managers.loot_tables import Chest, Items, Item, Material
from managers.locations import Area

# Flavour winning text.
win_text: list[str] = ["slays", "defeats", "conquers", "strikes down", "kills",
                       "obliterates", "slaps them with a wet fish killing",
                       "murders", "extinguishes the life of",
                       "removes the final sparkle of life from the eyes of",
                       "butchers",
                       ]


def durability_loss(leader: users.User) -> bool:
    """Gets if there should be durability loss on a weapon."""
    if leader.weapon > Material.NONE and random.randint(1, 2) == 1:
        leader.weapon_durability -= 1
        return True
    return False


class Participant():
    """A single participant inside of a party."""

    def __init__(self, user: discord.Member) -> None:
        self.user = user
        self.user_l = users.Manager.get(user.id)
        self.damage: list[int] = []
        self.deaths: int = 0

    def add_damage(self, damage: int) -> None:
        """Adds additional damage the user performed."""
        if damage == 0:
            return
        if damage > self.user_l.gold:
            damage = self.user_l.gold

        self.damage.append(damage)
        self.user_l.gold -= damage
        if self.user_l.gold == 0:
            self.deaths += 1
        self.user_l.save()

    def total_damage(self) -> int:
        """Gets the total damage performed."""
        return sum(self.damage)


class Party():
    """Represents several participants and their objective."""

    def __init__(self, leader: discord.Member,
                 entity: entities.Entity) -> None:
        self.leader = Participant(leader)
        self.entity = entity
        self.helpers: dict[int, Participant] = {}
        self.helpers[leader.id] = self.leader

    @property
    def count(self) -> int:
        """Total amount of party members."""
        return len(self.get_all())

    def get(self, user: discord.Member) -> Participant:
        """Gets a single user in a party, adding automatically."""
        helper = self.helpers.get(user.id, None)
        if not helper:
            helper = Participant(user)
            self.helpers[user.id] = helper
        return helper

    def add_damage(self, user: discord.Member, amount: int) -> None:
        """Adds damage that the party has done to the objective."""
        if amount == 0:
            return
        if amount > self.entity.health:
            amount = self.entity.health

        self.entity.health -= amount
        helper = self.get(user)
        helper.add_damage(amount)

    def get_all(self) -> list[Participant]:
        """Get all party members."""
        return [u for u in list(self.helpers.values()) if u.total_damage() > 0]


def loot_text(all_loot: list[Item], indent: int,
              new_area: Optional[Area]) -> str:
    """Generates all of the text for the loot acquired."""
    spacer: str = "ㅤ" * indent
    all_loot = [l for l in all_loot if l.type != Items.NONE]

    item_texts: list[str] = []
    for n, item in enumerate(all_loot):
        lfeed = '└' if n + 1 == len(all_loot) else '├'
        amt_text: str = ''
        if item.value > 1 and item.type != Items.WEAPON:
            amt_text = f" [{item.value}]"

        name = item.name.title()
        if new_area and item.type == Items.LOCATION:
            # Have special text for new location discoveries.
            area_name = "Unknown"
            if new_area.name:
                area_name = new_area.name.title()
            name = f"NEW AREA FOUND: {area_name}"

        item_texts.append(f"> {spacer}{lfeed} **{name}**{amt_text}")

        if item.type == Items.CHEST and isinstance(item, Chest):
            tchest_text = loot_text(item.items, indent + 1, new_area)
            item_texts.append(tchest_text)

    # Combine the text.
    full_loot = '\n'.join(item_texts)
    if len(item_texts) == 0:
        full_loot = f"> {spacer}└ **empty**"
    return full_loot


def loot(party: Party) -> str:
    """Attempts to attack the entity."""
    if party.count == 0:
        return "How did you manage to kill something with no one?"

    entity = party.entity
    leader_user = party.leader.user
    leader = users.Manager.get(leader_user.id)

    # Check if the leader loses durability on their weapon.
    loss_dur: bool = False
    if not entity.ischest:
        loss_dur = durability_loss(leader)

    all_loot = entity.get_loot()
    all_loot = [l for l in all_loot if l.type != Items.NONE]

    # Apply all loot to each participant.
    new_area: Optional[Area] = None
    helpers_exp: list[str] = []
    total_exp = party.entity.get_exp(leader.level)
    for n, helper in enumerate(party.get_all()):
        lfeed = '└' if n + 1 == party.count else '├'
        user = users.Manager.get(helper.user.id)
        exp = helper.total_damage() / entity.max_health * total_exp
        user.exp += exp
        user.kills += 1
        new_area = user.apply_loot(all_loot, party.count == 1)
        if helper.deaths > 0:
            user.deaths -= helper.deaths
        user.save()
        helpers_exp.append(f"> {lfeed} {helper.user} gained {exp:0.2f} exp.")
    full_help = '\n'.join(helpers_exp)

    if not new_area:
        all_loot = [l for l in all_loot if l.type != Items.LOCATION]

    # Creates the text for loot.
    full_loot = loot_text(all_loot, 0, new_area)

    # Additional notes:
    notes_list: list[str] = []
    if loss_dur:
        weapon_status = f"{leader_user} **loss durability** on their weapon."
        if leader.weapon_durability == 0:
            weapon_status = f"{leader_user} **broke** their weapon."
        notes_list.append(weapon_status)

    notes_full = ""
    if len(notes_list) > 0:
        notes_text = '\n> '.join(notes_list)
        notes_full = f"__**Notes**__:\n > {notes_text}\n\n"

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
    if entity.ischest:
        win = "heroically opens"
    return f"**{leader_user}** {win} **{entity.name}**!\n\n"\
        f"**Total Reward**: {total_exp:0.2f} exp\n"\
        f"__**Participant Exp**__:\n{full_help}\n\n"\
        f"{notes_full}"\
        f"> __**Loot**__:\n  {full_loot}\n\n"\
        f"{change_loc}"


class Dropdown(ui.Select):
    """Actions that can be performed against the entity."""

    def __init__(self, user: discord.Member, entity: entities.Entity):
        self.user = user
        self.user_l = users.Manager.get(user.id)
        self.entity = entity
        atk_label = "Attack"
        if entity.ischest:
            atk_label = "Open"

        options = [
            discord.SelectOption(
                label=atk_label, description=f"Choose to {atk_label.lower()}."),
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
        embed.description = f"**{self.user}** flees like a coward.\n"\
            f"Leaving {self.entity.get_exp(self.user_l.level):0.2f} exp.\n\n"\
            f"**{self.entity.name.title()}** begins to hunt again."
        file: Optional[discord.File] = None
        if self.entity.image:
            file = images.Manager.get(self.entity.image)
            if file:
                url = f"attachment://{self.entity.image}"
                embed.set_thumbnail(url=url)

        if self.values[0].lower() in ('attack', 'open'):

            embed.color = discord.Colour.from_str("#00ff08")
            if self.user_l.gold < self.entity.health:
                # Get help from another user.
                exp = self.entity.get_exp(self.user_l.level)
                damage = self.user_l.gold
                help_view = HelpMeView(self.user, self.entity, exp, damage)
                help_embed = help_view.get_panel()
                if file:
                    url = f"attachment://{self.entity.image}"
                    help_embed.set_thumbnail(url=url)

                # Register the "loss" callback.
                destruct = DestructableManager.get(msg.id)
                if destruct:
                    destruct.set_callback(help_view.loss_callback)
                    destruct.add_time(60)

                await msg.edit(embed=help_embed, view=help_view)
                return await res.send_message(f"You deal {damage} damage.",
                                              ephemeral=True, delete_after=30)
            party = Party(self.user, self.entity)
            party.add_damage(self.user, self.entity.health)
            embed.description = loot(party)
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

        # Create the new one.
        delete_after: Optional[int] = None
        if not self.entity.isboss:
            delete_after = 420
        await cached.reply(embed=embed, delete_after=delete_after, file=file)


class HelpMeView(ui.View):
    """Presents the help information to other players."""

    def __init__(self, user: discord.Member,
                 entity: entities.Entity,
                 exp_gain: float,
                 damage: int):
        self.user = user
        self.user_l = users.Manager.get(self.user.id)
        self.entity = entity

        self.party: Party = Party(user, entity)
        self.party.add_damage(user, damage)

        self.exp_gain: float = exp_gain
        self.iscomplete: bool = False
        super().__init__(timeout=None)

    def has_contributed(self, user: discord.Member) -> bool:
        """Checks if a user has contributed already."""
        helper = self.party.get(user)
        return helper.total_damage() > 0

    def get_panel(self) -> discord.Embed:
        """Produces the entities message."""
        embed = discord.Embed(title="REQUESTING HELP!")

        action = self.entity.get_action()
        cost = self.entity.health

        # Add all of the participants and their contributions.
        participants_full: str = ""
        all_help: list[str] = []
        if self.party.count == 0:
            participants_full = "__**Party**__:\n> empty\n\n"
        else:
            for helper in self.party.get_all():
                dmg = helper.total_damage()
                all_help.append(f"> **{helper.user}** performed {dmg} damage.")

            full_help = '\n  '.join(all_help)
            if len(all_help) == 0:
                full_help = " > empty"
            participants_full = f"__**Party**__:\n{full_help}\n\n"

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
        embed.set_footer(text=f"Note: Only other users {other_than} can help.")
        return embed

    async def loss_callback(self, msg: Optional[discord.Message]) -> None:
        """Called when the original message gets deleted."""
        self.user_l.set_combat(False)

        if self.iscomplete:
            return

        if not msg or not msg.reference or not msg.reference.cached_message:
            return

        party = self.party
        leader = party.leader

        # Generate all of the gold that was lost text.
        dead_text: list[str] = []
        if party.count == 0:
            dead_text.append("> empty")
        else:
            for helper in party.get_all():
                cost = helper.total_damage()
                dead_text.append(f"> {helper.user} lost {cost} gp.")
        dead_full = '\n'.join(dead_text)

        # Check the durability of the leaders weapon.
        loss_dur = durability_loss(leader.user_l)

        notes_list: list[str] = []
        if loss_dur:
            leader.user_l.save()
            weapon_status = f"{leader.user} **loss durability** on their weapon."
            if leader.user_l.weapon_durability == 0:
                weapon_status = f"{leader.user} **broke** their weapon."
            notes_list.append(weapon_status)

        notes_full = ""
        if len(notes_list) > 0:
            notes_text = '\n> '.join(notes_list)
            notes_full = f"__**Notes**__:\n > {notes_text}\n\n"

        leader = party.leader
        partytxt = "The **party**" if party.count > 1 else f"**{leader.user}**"
        description = f"{partytxt} has failed to kill **{self.entity.name}**.\n\n"\
            f"{notes_full}"\
            f"__**Losses**__:\n{dead_full}"

        embed = discord.Embed(description=description)
        embed.color = discord.Colour.from_str("#ff0f08")
        embed.set_footer(text="Better luck next time!")
        file: Optional[discord.File] = None
        if self.entity.image:
            file = images.Manager.get(self.entity.image)
            if file:
                url = f"attachment://{self.entity.image}"
                embed.set_thumbnail(url=url)

        delete_after: Optional[int] = None
        if not party.entity.isboss:
            delete_after = 360
        cached = msg.reference.cached_message
        await cached.reply(embed=embed, delete_after=delete_after, file=file)

    @ui.button(label='HELP [ALL]', style=discord.ButtonStyle.red,
               custom_id='helpme_view:help_all')
    async def help_all(self, interaction: discord.Interaction, button: ui.Button):
        user = users.Manager.get(interaction.user.id)
        await self.help(interaction, user.gold)

    @ui.button(label='HELP [1000]', style=discord.ButtonStyle.red,
               custom_id='helpme_view:help_1k')
    async def help_1000(self, interaction: discord.Interaction, button: ui.Button):
        user = users.Manager.get(interaction.user.id)
        amount = 1000 if user.gold > 1000 else user.gold
        await self.help(interaction, amount)

    @ui.button(label='HELP [100]', style=discord.ButtonStyle.red,
               custom_id='helpme_view:help_100')
    async def help_100(self, interaction: discord.Interaction, button: ui.Button):
        user = users.Manager.get(interaction.user.id)
        amount = 100 if user.gold > 100 else user.gold
        await self.help(interaction, amount)

    async def help(self, interaction: discord.Interaction, amount: int) -> None:
        """Provides help to a user."""
        res = interaction.response
        msg = interaction.message
        user = interaction.user
        guild = interaction.guild
        if not guild or not isinstance(user, discord.Member):
            return await res.send_message("Could not get your server id.",
                                          ephemeral=True, delete_after=30)

        # Check that the user has the minigame role.
        setting = settings.Manager.get(guild.id)
        role_id = setting.minigame_role_id
        minigame_role: Optional[discord.Role] = None

        # Validate the role is set to play.
        minigame_role = await get_role(interaction.client, guild.id, role_id)
        if not minigame_role:
            await res.send_message("Minigame role may be current unset.",
                                   ephemeral=True,
                                   delete_after=30)
            return

        # User does not have the role and cannot play.
        if minigame_role not in user.roles:
            # Shows and optional text for easy role access.
            in_channel: str = ""
            if setting.react_role_channel_id > 0:
                in_channel = f"\nGo to <#{setting.react_role_channel_id}> to get the"\
                    " required role."
            await res.send_message(f"You need to select the "
                                   f"**{minigame_role}** role to do that. "
                                   f"{in_channel}",
                                   ephemeral=True,
                                   delete_after=30)
            return

        if amount == 0:
            return await res.send_message("You do not have any gold.",
                                          ephemeral=True, delete_after=15)

        if not msg or not msg.reference or not msg.reference.cached_message:
            print("Message cache failed on entity spawning.")
            return

        # Cannot do a final blow, so add them as a participant.
        if amount < self.entity.health:
            extension: int = 60
            if self.entity.isboss:
                extension = 1800
            DestructableManager.extend(msg.id, extension)

            self.party.add_damage(user, amount)
            help_embed = self.get_panel()

            await msg.edit(embed=help_embed)
            return await res.send_message(f"You deal {amount} damage.",
                                          ephemeral=True, delete_after=15)

        # Enough gold to do the final blow.
        self.party.add_damage(user, self.entity.health)

        self.user_l.set_combat(False)

        self.iscomplete = True
        await res.send_message("You deal the fatal blow!",
                               ephemeral=True, delete_after=30)

        # Build the final embed and send it.
        embed = discord.Embed()
        embed.color = discord.Colour.from_str("#00ff08")
        embed.description = loot(self.party)

        file: Optional[discord.File] = None
        if self.entity.image:
            file = images.Manager.get(self.entity.image)
            if file:
                url = f"attachment://{self.entity.image}"
                embed.set_thumbnail(url=url)

        cached = msg.reference.cached_message
        # Delete the old destructable.
        await DestructableManager.remove_one(msg.id, True)

        # Create a new one.
        delete_after: Optional[int] = None
        if not self.party.entity.isboss:
            delete_after = 420
        await cached.reply(embed=embed, delete_after=delete_after, file=file)


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
        gained_exp = self.entity.get_exp(user_l.level)

        gold_warning: str = ""
        if user_l.gold < cost:
            gold_warning = "__WARNING__: You do not have enough gold.\n"\
                "By attacking, you risk losing all of it unless someone helps."

        loc_name = 'Unknown'
        atk: str = "Attack"
        if self.entity.ischest:
            atk = "Open"
        if self.entity.location.name:
            loc_name = self.entity.location.name.title()
        embed.color = discord.Colour.from_str("#F1C800")
        embed.description = f"**{self.user}** {action} **{self.entity.name}**!\n"\
            f"**Location**: {loc_name}\n"\
            f"**Health**: {cost}\n\n"\
            "> __**Options**:__\n"\
            f"> ├ **{atk}**: Costing {cost} gp, gaining {gained_exp:0.2f} exp.\n"\
            "> └ **Flee**: Flee, keeping your gold.\n\n"\
            f"{gold_warning}"
        embed.set_footer(text=f"Current gold: {user_l.gold} gp")
        return embed

    async def loss_callback(self, msg: Optional[discord.Message]):
        """Cleans up after a loss."""
        self.user_l.set_combat(False)
