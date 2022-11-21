import configparser
import pathlib
from typing import Optional

CONFIG_FILENAME = 'config.ini'


class ProjectConfig():
    def __init__(self, config: configparser.ConfigParser) -> None:
        self._config = config

    @property
    def debug(self) -> bool:
        default = self._config['DEFAULT']
        if default is None:
            raise ValueError("'DEFAULT' is unset in configuration file.")
        val = default.get('Debug', 'False')
        return val.lower() == "true"

    @property
    def discord_token(self) -> str:
        discord = self._config['DISCORD']
        if discord is None:
            raise ValueError("'DISCORD' is unset in configuration file.")
        val = discord.get('Token', 'unset')
        if val is None:
            return ""
        return val

    @property
    def discord_prefix(self) -> str:
        discord = self._config['DISCORD']
        if discord is None:
            raise ValueError("'DISCORD' is unset in configuration file.")
        val = discord.get('Prefix', '?')
        if val is None or val == "":
            return '?'
        return val

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
            if token == 'unset' or prefix == "":
                raise ValueError()
        except (ValueError, Exception) as err:
            raise ValueError("invalid values in configuration file.")
        return ProjectConfig(config)
