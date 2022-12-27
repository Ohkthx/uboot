"""User based views."""
from typing import Optional
from datetime import datetime, timezone

import discord
from discord import ui

from managers import users
from managers.locations import Area


class LocationDropdown(ui.Select):
    """Allows the user to select a new location."""

    def __init__(self, user: users.User) -> None:
        options: list[discord.SelectOption] = []
        for location in user.locations.get_unlocks():
            options.append(discord.SelectOption(label=location))
        super().__init__(options=options,
                         placeholder="Recall to a new location.",
                         custom_id="user_location_dropdown")

    async def callback(self, interaction: discord.Interaction):
        """Called when the menu is selected."""
        res = interaction.response

        # Changes the users location, only if it is discovered.
        user = users.Manager.get(interaction.user.id)
        changed = user.change_location(self.values[0])
        if interaction.message and isinstance(interaction.user, discord.User):
            embed = UserView.get_panel(interaction.user)
            await interaction.message.edit(embed=embed)

        if not changed:
            await res.send_message("Unknown location, have you discovered it?",
                                   ephemeral=True,
                                   delete_after=30)
            return

        user.save()
        await res.send_message(f"Location set to {self.values[0].title()}.",
                               ephemeral=True,
                               delete_after=30)


class UserView(ui.View):
    """User View that can be interacted with to make user changes."""

    def __init__(self, bot: discord.Client) -> None:
        self.bot = bot
        self.user: Optional[discord.User] = None
        super().__init__(timeout=None)

    def set_user(self, user: discord.User) -> None:
        """Sets the user so their locations can be used in the dropdown."""
        self.user = user
        user_l = users.Manager.get(user.id)
        self.add_item(LocationDropdown(user_l))

    @staticmethod
    def get_panel(user: discord.User) -> discord.Embed:
        """Gets the user stats for the user provided."""
        # Get the local user.
        user_l = users.Manager.get(user.id)
        title = '' if user_l.button_press == 0 else ', the Button Presser'

        if user.bot:
            title = ', the Scholar'

        # Calculate the users age based on when they joined Discord.
        age = datetime.now(timezone.utc) - user.created_at
        year_str = '' if age.days // 365 < 1 else f"{age.days//365} year(s), "
        day_str = '' if age.days % 365 == 0 else f"{int(age.days%365)} day(s)"

        powerhour_text = ""
        if user_l.powerhour:
            powerhour_text = "**powerhour**: enabled\n"

        color = discord.Colour.from_str("#00ff08")
        desc = f"**{user}{title}**\n\n"\
            f"**id**: {user.id}\n"\
            f"**age**: {year_str}{day_str}\n"\
            f"**deaths**: {user_l.deaths}\n"\
            f"**level**: {user_l.level}\n"\
            f"**gold**: {user_l.gold} gp\n"\
            f"**messages**: {user_l.msg_count}\n"\
            f"{powerhour_text}"\
            f"**gold multiplier**: {(user_l.gold_multiplier):0.2f}\n\n"\
            "> __Gamble__:\n"\
            f"> ├ **total**: {user_l.gambles}\n"\
            f"> ├ **won**: {user_l.gambles_won}\n"\
            f"> ├ **win-rate**: {user_l.win_rate():0.2f}%\n"\
            f"> └ **minimum**: {user_l.minimum(20)} gp\n\n"\
            "> __Slaying__:\n"\
            f"> ├ **exp**: {user_l.exp}\n"\
            f"> ├ **total**: {user_l.monsters}\n"\
            f"> ├ **killed**: {user_l.kills}\n"\
            f"> └ **fled**: {user_l.monsters - user_l.kills}\n"

        c_location: str = 'Unknown'
        if user_l.c_location.name:
            c_location = user_l.c_location.name.title()
        embed = discord.Embed(description=desc, color=color)
        embed.set_footer(text=f"Current Location: {c_location}")
        embed.set_thumbnail(url=user.display_avatar.url)
        return embed


async def setup(bot: discord.Client) -> None:
    """This is called by process that loads extensions."""
    bot.add_view(UserView(bot))
