"""Handles twitch integrations."""
from typing import Tuple
import discord
import requests

from .helper import (get_member, get_role)
from config import TwitchConfig
from managers import users, settings
from managers.logs import Log


class TwitchHandler:
    """Handles twitch integrations."""

    def __init__(self, config: TwitchConfig) -> None:
        self._config = config
        self._oauth_token = ""

    @property
    def client_id(self) -> str:
        return self._config.token

    @property
    def secret(self) -> str:
        return self._config.secret

    async def add_role(self, client: discord.Client, member: discord.Member, role: discord.Role):
        """"Removes the streamer role to the user."""
        if role in member.roles:
            return

        try:
            # Add the role.
            await member.add_roles(role)
            Log.action(f"Adding {role.name} role to {member}.",
                       guild_id=member.guild.id, user_id=member.id)
        except BaseException as exc:
            Log.error(f"Could not add {role.name} role to {str(member)}.\n"
                      f"{exc}",
                      guild_id=member.guild.id, user_id=member.id)

    async def remove_role(self, client: discord.Client, member: discord.Member, role: discord.Role):
        """"Removes the streamer role to the user."""
        if role not in member.roles:
            return

        try:
            # Remove the role.
            await member.remove_roles(role)
            Log.action(f"Removing {role.name} role from {member}.",
                       guild_id=member.guild.id, user_id=member.id)
        except BaseException as exc:
            Log.error(f"Could not remove {role.name} role from {str(member)}.\n"
                      f"{exc}",
                      guild_id=member.guild.id, user_id=member.id)

    async def check_streams(self, client: discord.Client, setting: settings.Settings, guild_id: int):
        """"Check all possibly live streams."""
        tset = setting.twitch
        if tset.role_id == 0 or tset.streaming_role_id == 0:
            return
        elif len(tset.titles) == 0 or tset.titles[0] == "unset":
            return

        # Get the role to assign to the promoters.
        promoter_role = await get_role(client, guild_id, tset.role_id)
        if not promoter_role:
            Log.error("Could not obtain promoter role for updating stream status.",
                      guild_id=guild_id)
            return

        # Get the role to assign to the new streamer.
        twitch_role = await get_role(client, guild_id, tset.streaming_role_id)
        if not twitch_role:
            Log.error("Could not obtain twitch role for updating stream status.",
                      guild_id=guild_id)
            return

        # Get all users streaming with promoter role.
        streamers: list[Tuple[discord.Member, str]] = []
        for member in promoter_role.members:
            for activity in member.activities:
                if isinstance(activity, discord.Streaming) and activity.platform == "Twitch":
                    streamers.append((member, activity.twitch_name))

        # Get all users streaming with twitch role.
        for member in twitch_role.members:
            found: bool = False
            for activity in member.activities:
                if isinstance(activity, discord.Streaming) and activity.platform == "Twitch":
                    found = True
            # User is no longer streaming.
            if not found:
                await self.remove_role(client, member, twitch_role)

        # Attempt to pull their info.
        for member, twitch_name in streamers:
            title, game, online = self.get_stream_info(twitch_name)
            if not online:
                await self.remove_role(client, member, twitch_role)
                continue
            elif game.lower() != "ultima online":
                await self.remove_role(client, member, twitch_role)
                continue

            # Check the titles.
            found: bool = False
            for t in tset.titles:
                if t.lower() in title.lower():
                    found = True
                    break

            if not found:
                await self.remove_role(client, member, twitch_role)
                continue

            # Add the role for streaming
            await self.add_role(client, member, twitch_role)

    def get_game_name(self, game_id: str) -> str:
        """Obtains the game name from the API."""
        url = f"https://api.twitch.tv/helix/games?id={game_id}"
        response = requests.get(url, headers=self.get_headers())

        data = response.json()['data']
        if data:
            return data[0]['name']
        return "Unknown Game"

    def get_stream_info(self, username: str) -> Tuple[str, str, bool]:
        """Obtains various stream information for a user."""
        url = f"https://api.twitch.tv/helix/streams?user_login={username}"
        response = requests.get(url, headers=self.get_headers())

        data = response.json()['data']
        if len(data) == 0 or response.status_code != 200:
            return "", "", False

        # Extract the information from the data.
        title: str = data[0]['title']
        game_id: str = data[0]['game_id']

        # Get the game information.
        game_name: str = self.get_game_name(game_id)
        return title, game_name, True

    def get_token(self) -> str:
        """Checks the status of the OAuth Token."""
        url = "https://id.twitch.tv/oauth2/validate"
        headers = {'Authorization': f"Bearer {self._oauth_token}"}
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            return self._oauth_token

        # Invalid token, get a new one.
        url = "https://id.twitch.tv/oauth2/token"
        body = {
            'client_id': self.client_id,
            'client_secret': self.secret,
            'grant_type': "client_credentials"
        }
        response = requests.post(url, data=body)
        if response.status_code != 200:
            return ""

        # Update the token.
        self._oauth_token = response.json()['access_token']
        return self._oauth_token

    def get_headers(self):
        """Gets the headers to send to the API."""
        return {
            'Client-ID': self.client_id,
            'Authorization': f"Bearer {self.get_token()}"
        }
