import traceback
from typing import Union

import discord
from discord import ui


class ReasonModal(ui.Modal, title='Reason'):
    def __init__(self, to_user: Union[discord.Member, None],
                 from_user: Union[discord.Member, None],
                 title: str,
                 text: str,
                 color: discord.Color) -> None:
        self.to_user = to_user
        self.from_user = from_user
        self.text_title = title
        self.text_prefix = text
        self.text_color = color
        super().__init__()

    reason = ui.TextInput(
        label='Reasoning that will be sent to user',
        style=discord.TextStyle.long,
        placeholder='Type your reason here...',
        required=True,
        max_length=300,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        res = interaction.response
        embed = discord.Embed(title=self.text_title,
                              color=self.text_color,
                              description=f"{self.text_prefix}\n"
                              f"**Reason**:\n```{self.reason.value}```")
        if self.from_user:
            embed.set_footer(text=f"Reviewed by {self.from_user}")
        if self.to_user:
            await self.to_user.send(embed=embed)
        await res.send_message(embed=embed)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        res = interaction.response
        await res.send_message('Oops! Something went wrong, please notify an '
                               'admin for additional help.',
                               ephemeral=True,
                               delete_after=60)
        traceback.print_tb(error.__traceback__)
