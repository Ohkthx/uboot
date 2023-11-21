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

    async def add_role(self, client: discord.Client, guild_id: int, user_id: int, role_id: int):
        """"Gives the streamer role to the user."""
        # Get the role to assign to the new streamer.
        twitch_role = await get_role(client, guild_id, role_id)
        if not twitch_role:
            Log.error("Could not obtain twitch role for updating stream status.",
                      guild_id=guild_id, user_id=user_id)
            return

        # Get the member profile to pull current roles.
        member = await get_member(client, guild_id, user_id)
        if not member:
            Log.error(f"Could not obtain member account for updating stream status.",
                      guild_id=guild_id, user_id=user_id)
            return

        if twitch_role in member.roles:
            return

        # Add the role.
        try:
            await member.add_roles(twitch_role)
            Log.action(f"Adding {twitch_role.name} role from {member}.",
                       guild_id=guild_id, user_id=user_id)
        except BaseException as exc:
            Log.error(f"Could not add {twitch_role.name} role to {str(member)}.\n"
                      f"{exc}",
                      guild_id=guild_id, user_id=user_id)

    async def remove_role(self, client: discord.Client, guild_id: int, user_id: int, role_id: int):
        """"Removes the streamer role to the user."""
        # Get the role to assign to the new streamer.
        twitch_role = await get_role(client, guild_id, role_id)
        if not twitch_role:
            Log.error("Could not obtain twitch role for updating stream status.",
                      guild_id=guild_id, user_id=user_id)
            return

        # Get the member profile to pull current roles.
        member = await get_member(client, guild_id, user_id)
        if not member:
            Log.error(f"Could not obtain member account for updating stream status.",
                      guild_id=guild_id, user_id=user_id)
            return

        if twitch_role not in member.roles:
            return

        # Remove the role.
        try:
            await member.remove_roles(twitch_role)
            Log.action(f"Removing {twitch_role.name} role from {member}.",
                       guild_id=guild_id, user_id=user_id)
        except BaseException as exc:
            Log.error(f"Could not remove {twitch_role.name} role from {str(member)}.\n"
                      f"{exc}",
                      guild_id=guild_id, user_id=user_id)

    async def check_streams(self, client: discord.Client, setting, guild_id: int):
        """"Check all possibly live streams."""
        tset = setting.twitch
        if tset.role_id == 0 or tset.streaming_role_id == 0:
            return
        elif len(tset.titles) == 0 or tset.titles[0] == "unset":
            return

        # All streamer accounts.
        all_users = users.Manager.get_all()
        streamers = [u for u in all_users if u.is_streamer]
        if len(streamers) == 0:
            return

        # Attempt to pull their info.
        for s in streamers:
            title, game, online = self.get_stream_info(s.stream_name)
            if not online:
                await self.remove_role(client, guild_id, s.id, tset.streaming_role_id)
                continue
            elif game.lower() != "ultima online":
                await self.remove_role(client, guild_id, s.id, tset.streaming_role_id)
                continue

            # Check the titles.
            found: bool = False
            for t in tset.titles:
                if t.lower() in title.lower():
                    found = True
                    break

            if not found:
                await self.remove_role(client, guild_id, s.id, tset.streaming_role_id)
                continue

            # Add the role for streaming
            title_text = f", [{game}] {title}"
            print(f"{s.stream_name}, streaming: {online}{title_text}")
            await self.add_role(client, guild_id, s.id, tset.streaming_role_id)

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
