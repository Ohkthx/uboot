"""Manages the configuration file for the entire application. By default,
the applications configuration file name is 'config.int'.
Performs basic error checking on the configuration file as well.
"""
import pathlib
import configparser
from typing import Optional

CONFIG_FILENAME = 'config.ini'


class DiscordConfig:
    """Configuration Settings for Discords API."""

    def __init__(self, config: configparser.SectionProxy) -> None:
        self._config = config

    @property
    def token(self) -> str:
        """Token for access to Discord API.
        Default: unset
        """
        val = self._config.get('Token', fallback='unset')
        if not val:
            return "unset"
        return val

    @property
    def prefix(self) -> str:
        """Command prefix for the bot to register what is a command.
        Default: [
        """
        val = self._config.get('Prefix', fallback='[')
        if val is None or val == "":
            return '['
        return val

    @property
    def owner_id(self) -> int:
        """Owner of the bots Discord ID, it is most likely a large integer.
        Default: 0
        """
        return self._config.getint('OwnerId', 0)

    @property
    def ccserver_dm_id(self) -> int:
        """DM Channel ID of the bots command server.
        Default: 0
        """
        return self._config.getint('CCDMId', 0)


class GeneralConfig:
    """General configurations, parent to all sub-configurations."""

    def __init__(self, config: configparser.ConfigParser) -> None:
        self._config = config

        # Throw an error since Discord config is essential for running.
        if not config.has_section('DISCORD'):
            raise ValueError("'DISCORD' is unset in configuration file.")
        self._discord = DiscordConfig(config['DISCORD'])

    @property
    def discord(self) -> DiscordConfig:
        """Discord configurations."""
        return self._discord

    @property
    def debug(self) -> bool:
        """Controls if the program is running in DEBUG mode.
        Default: 'False'
        """
        return self._config.getboolean('DEFAULT', 'Debug', fallback=False)

    @staticmethod
    def make_default_config() -> bool:
        """Creates a default configuration for the application. The file will
        be titled CONFIG_FILENAME ('config.ini' by default.)
        """
        # If the file exists ignore.
        if pathlib.Path(CONFIG_FILENAME).is_file():
            return False

        # Initialize each category and the default values.
        config = configparser.ConfigParser()
        config['DEFAULT'] = {}
        config['DEFAULT']['Debug'] = 'False'
        config['DISCORD'] = {}
        config['DISCORD']['Token'] = 'unset'
        config['DISCORD']['Prefix'] = '['
        config['DISCORD']['OwnerId'] = '0'
        config['DISCORD']['CCDMId'] = '0'

        # Save it locally.
        with open(CONFIG_FILENAME, 'w', encoding='utf-8') as configfile:
            config.write(configfile)
        return True

    @staticmethod
    def load_config() -> Optional['GeneralConfig']:
        """Attempts to load the local configuration file into memory."""
        # Cannot load a non-existing file.
        if not pathlib.Path(CONFIG_FILENAME).is_file():
            return None

        config = configparser.ConfigParser()
        config.read(CONFIG_FILENAME)

        if not config.has_section('DISCORD'):
            raise ValueError("'DISCORD' section missing from configuration.")

        try:
            token = config.get('DISCORD', 'Token', fallback='unset')
            if token == 'unset':
                raise ValueError()
        except (ValueError, Exception) as err:
            raise ValueError("invalid values in configuration file.") from err
        return GeneralConfig(config)
