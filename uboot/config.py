import configparser
import pathlib
from typing import Optional

CONFIG_FILENAME = 'config.ini'


class DiscordConfig():
    def __init__(self, config) -> None:
        self._config = config

    @property
    def token(self) -> str:
        val = self._config.get('Token', 'unset')
        if val is None:
            return ""
        return val

    @property
    def prefix(self) -> str:
        val = self._config.get('Prefix', '?')
        if val is None or val == "":
            return '?'
        return val

    @property
    def market_id(self) -> int:
        val = self._config.get('MarketChannelId', '0')
        return int(val)

    @property
    def market_expiration(self) -> int:
        val = self._config.get('ExpirationDays', '0')
        return int(val)


class ProjectConfig():
    def __init__(self, config: configparser.ConfigParser) -> None:
        self._config = config
        discord = self._config['DISCORD']
        if discord is None:
            raise ValueError("'DISCORD' is unset in configuration file.")
        self._discord = DiscordConfig(discord)

    @property
    def discord(self) -> DiscordConfig:
        return self._discord

    @property
    def debug(self) -> bool:
        default = self._config['DEFAULT']
        if default is None:
            raise ValueError("'DEFAULT' is unset in configuration file.")
        val = default.get('Debug', 'False')
        return val.lower() == "true"

    @staticmethod
    def make_default_config() -> bool:
        if pathlib.Path(CONFIG_FILENAME).is_file():
            return False
        config = configparser.ConfigParser()
        config['DEFAULT'] = {}
        config['DEFAULT']['Debug'] = 'False'
        config['DISCORD'] = {}
        config['DISCORD']['Token'] = 'unset'
        config['DISCORD']['Prefix'] = '?'
        config['DISCORD']['MarketChannelId'] = '0'
        config['DISCORD']['ExpirationDays'] = '30'
        with open(CONFIG_FILENAME, 'w') as configfile:
            config.write(configfile)
        return True

    @staticmethod
    def load_config() -> Optional['ProjectConfig']:
        if not pathlib.Path(CONFIG_FILENAME).is_file():
            return
        config = configparser.ConfigParser()
        config.read(CONFIG_FILENAME)

        default = config['DEFAULT']
        if default is None:
            raise ValueError("'DEFAULT' is unset in configuration file.")
        discord = config['DISCORD']
        if discord is None:
            raise ValueError("'DISCORD' is unset in configuration file.")
        try:
            token = str(discord.get('Token', 'unset'))
            prefix = str(discord.get('Prefix', '?'))
            int(discord.get('MarketChannelId', '0'))
            int(discord.get('ExpirationDays', '0'))
            if token == 'unset' or prefix == "":
                raise ValueError()
        except (ValueError, Exception) as err:
            raise ValueError("invalid values in configuration file.")
        return ProjectConfig(config)
