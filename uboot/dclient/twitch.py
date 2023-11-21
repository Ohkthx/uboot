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
            print("Could not update the streaming role of the user.")

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
        oauth: str = self.get_oauth_token()
        for s in streamers:
            print(f"Checking: {s.id}")
            title, game, online = self.get_stream_info(oauth, s.stream_name)
            if not online:
                await self.remove_role(client, guild_id, s.id, tset.streaming_role_id)
                continue
            elif game.lower() != "ultima online":
                await self.remove_role(client, guild_id, s.id, tset.streaming_role_id)
                continue

            # Check the titles.
            lower_check = [chk.lower() for chk in tset.titles]
            title_parts = title.split(" ")
            found: bool = False
            for t in title_parts:
                if t.lower() in lower_check:
                    found = True
                    break

            if not found:
                await self.remove_role(client, guild_id, s.id, tset.streaming_role_id)
                continue

            # Add the role for streaming
            title_text = f", [{game}] {title}"
            print(f'{s.stream_name}, streaming: {online}{title_text}')
            await self.add_role(client, guild_id, s.id, tset.streaming_role_id)

    def get_headers(self, oauth: str):
        """Gets the headers to send to the API."""
        return {
            'Client-ID': self._config.token,
            'Authorization': f'Bearer {oauth}'
        }

    def get_oauth_token(self) -> str:
        """Obtains an oauth token from the API."""
        url = 'https://id.twitch.tv/oauth2/token'
        body = {
            'client_id': self._config.token,
            'client_secret': self._config.secret,
            'grant_type': 'client_credentials'
        }
        response = requests.post(url, data=body)
        return response.json()['access_token']

    def get_game_name(self, oauth: str, game_id: str) -> str:
        """Obtains the game name from the API."""
        url = f'https://api.twitch.tv/helix/games?id={game_id}'
        response = requests.get(url, headers=self.get_headers(oauth))

        data = response.json()['data']
        if data:
            return data[0]['name']
        return "Unknown Game"

    def get_stream_info(self, oauth: str, username: str) -> Tuple[str, str, bool]:
        """Obtains various stream information for a user."""
        url = f'https://api.twitch.tv/helix/streams?user_login={username}'
        response = requests.get(url, headers=self.get_headers(oauth))

        data = response.json()['data']
        if len(data) == 0:
            return "", "", False

        # Extract the information from the data.
        title = data[0]['title']
        game_id = data[0]['game_id']
        game_name = self.get_game_name(oauth, game_id)
        return title, game_name, True
