"""Settings for server to direct traffic and other basic settings.
The associated manager handles all of the loading and saving to the database.
It is equipped with finding settings based on certain parameters.
"""
import os
import pathlib
import configparser
from typing import Optional

from .logs import Log

# Required sections for full operation.
REQUIRED_SECTIONS = ["MARKET", "REACTROLE", "SUPPORT", "SUGGESTION", "SUBGUILD",
                     "LOTTO", "MINIGAME", "ALIAS"]


class Market():
    """Settings for market and trade channel."""

    def __init__(self, config: configparser.SectionProxy) -> None:
        self._config = config

    def __str__(self) -> str:
        """Overrides the string representation."""
        return f"Channel Id: {self.channel_id}\n"\
            f"Expiration Days: {self.expiration}"

    @property
    def channel_id(self) -> int:
        """Market Channel Id"""
        return self._config.getint('CHANNELID', 0)

    @property
    def expiration(self) -> int:
        """Amount of time until trades expired."""
        return self._config.getint('EXPIRATION', 15)


class ReactRole():
    """Settings for reaction role assignment."""

    def __init__(self, config: configparser.SectionProxy) -> None:
        self._config = config

    def __str__(self) -> str:
        """Overrides the string representation."""
        return f"Channel Id: {self.channel_id}\n"\
            f"Message Id: {self.msg_id}"

    @property
    def channel_id(self) -> int:
        """Channel Id where the reactions will assign roles."""
        return self._config.getint('CHANNELID', 0)

    @property
    def msg_id(self) -> int:
        """Message the reactions are attached to."""
        return self._config.getint('MESSAGEID', 0)


class Support():
    """Settings for support assignment."""

    def __init__(self, config: configparser.SectionProxy) -> None:
        self._config = config

    def __str__(self) -> str:
        """Overrides the string representation."""
        return f"Channel Id: {self.channel_id}\n"\
            f"Role Id: {self.role_id}"

    @property
    def channel_id(self) -> int:
        """Channel Id where the support will be provided."""
        return self._config.getint('CHANNELID', 0)

    @property
    def role_id(self) -> int:
        """Role Id of users who act as support."""
        return self._config.getint('SUPPORTROLEID', 0)


class Suggestion():
    """Settings for the suggestion channel."""

    def __init__(self, config: configparser.SectionProxy) -> None:
        self._config = config

    def __str__(self) -> str:
        """Overrides the string representation."""
        return f"Channel Id: {self.channel_id}\n"\
            f"Role Id: {self.role_id}"

    @property
    def channel_id(self) -> int:
        """Channel Id where the suggestions will be provided."""
        return self._config.getint('CHANNELID', 0)

    @property
    def role_id(self) -> int:
        """Role Id of users who act as reviewers."""
        return self._config.getint('REVIEWROLEID', 0)


class SubGuild():
    """Settings for the subguilds."""

    def __init__(self, config: configparser.SectionProxy) -> None:
        self._config = config

    def __str__(self) -> str:
        """Overrides the string representation."""
        return f"Channel Id: {self.channel_id}\n"\
            f"Review Channel Id: {self.review_channel_id}"

    @property
    def channel_id(self) -> int:
        """Channel Id where the subguilds will be hosted."""
        return self._config.getint('CHANNELID', 0)

    @property
    def review_channel_id(self) -> int:
        """Channel Id of users who review subguild requests."""
        return self._config.getint('REVIEWCHANNELID', 0)


class Lotto():
    """Settings for the lotto system."""

    def __init__(self, config: configparser.SectionProxy) -> None:
        self._config = config

    def __str__(self) -> str:
        """Overrides the string representation."""
        return f"Role Id: {self.role_id}\n"\
            f"Winner Role Id: {self.winner_role_id}"

    @property
    def role_id(self) -> int:
        """Role Id of lotto participants."""
        return self._config.getint('ROLEID', 0)

    @property
    def winner_role_id(self) -> int:
        """Role Id given to winners of the lotto."""
        return self._config.getint('WINNERROLEID', 0)


class MiniGame():
    """Settings for the minigame system."""

    def __init__(self, config: configparser.SectionProxy) -> None:
        self._config = config

    def __str__(self) -> str:
        """Overrides the string representation."""
        return f"Role Id: {self.role_id}"

    @property
    def role_id(self) -> int:
        """Role Id that allows users to play the minigames."""
        return self._config.getint('ROLEID', 0)


class Alias():
    """Settings for the alias system."""

    def __init__(self, config: configparser.SectionProxy) -> None:
        self._config = config

    def __str__(self) -> str:
        """Overrides the string representation."""
        return f"Channel Id: {self.channel_id}"

    @property
    def channel_id(self) -> int:
        """Channel Id where the embeds for aliases are held."""
        return self._config.getint('CHANNELID', 0)


class Settings():
    """Representation of a guilds settings."""

    def __init__(self, config: configparser.ConfigParser) -> None:
        self._update(config)

    def _update(self, config: configparser.ConfigParser) -> None:
        """Updates the local configs and the bindings attached."""
        self._config = config

        # Throw an error if a required section is missing.
        for section in REQUIRED_SECTIONS:
            if not config.has_section(section):
                raise ValueError(
                    f"'{section}' is unset in configuration file.")

        self.market = Market(config['MARKET'])
        self.reactrole = ReactRole(config['REACTROLE'])
        self.support = Support(config['SUPPORT'])
        self.suggestion = Suggestion(config['SUGGESTION'])
        self.subguild = SubGuild(config['SUBGUILD'])
        self.lotto = Lotto(config['LOTTO'])
        self.minigame = MiniGame(config['MINIGAME'])
        self.alias = Alias(config['ALIAS'])

    @property
    def guild_id(self) -> int:
        """Guild Id belonging to the discord server."""
        return self._config.getint('DEFAULT', 'GUILDID', fallback=False)

    @property
    def filename(self) -> str:
        """Name of the file for the guilds settings."""
        return f"configs/{self.guild_id}.ini"

    def update_config(self) -> bool:
        """Checks for updates for the configuration file."""
        if not os.path.exists("configs"):
            os.makedirs("configs")

        filename = f"configs/temp_{self.guild_id}.ini"

        # If the file exists ignore.
        if not pathlib.Path(filename).is_file():
            return False

        config = configparser.ConfigParser(inline_comment_prefixes=';')
        config.read(filename)
        self._update(config)

        os.replace(filename, self.filename)
        return True

    @staticmethod
    def make_default_config(guild_id: int) -> 'Settings':
        """Creates a default configuration for the guild."""
        if not os.path.exists("configs"):
            os.makedirs("configs")

        filename = f"configs/{guild_id}.ini"

        # If the file exists ignore.
        if pathlib.Path(filename).is_file():
            config = configparser.ConfigParser(inline_comment_prefixes=';')
            config.read(filename)
            return Settings(config)

        # Initialize each category and the default values.
        config = configparser.ConfigParser(inline_comment_prefixes=';')
        config['DEFAULT'] = {}
        config['DEFAULT']['GUILDID'] = f'{guild_id} ; id of the server/guild'

        config['REACTROLE'] = {}
        config['REACTROLE']['CHANNELID'] = '0 ; channel id for the react msg'
        config['REACTROLE']['MESSAGEID'] = '0 ; message id for the reactions'

        config['MARKET'] = {}
        config['MARKET']['CHANNELID'] = '0 ; channel id for the market forum'
        config['MARKET']['EXPIRATION'] = '15 ; amount of days until expiration'

        config['SUPPORT'] = {}
        config['SUPPORT']['CHANNELID'] = '0 ; channel id to get support'
        config['SUPPORT']['SUPPORTROLEID'] = '0 ; role id for providing support'

        config['SUGGESTION'] = {}
        config['SUGGESTION']['CHANNELID'] = '0 ; channel id for suggest forum'
        config['SUGGESTION']['REVIEWROLEID'] = '0 ; role id for approving'

        config['SUBGUILD'] = {}
        config['SUBGUILD']['REVIEWCHANNELID'] = '0 ; channel id to review guilds'
        config['SUBGUILD']['CHANNELID'] = '0 ; channel id to host guild info'

        config['LOTTO'] = {}
        config['LOTTO']['ROLEID'] = '0 ; role id for lotto participants'
        config['LOTTO']['WINNERROLEID'] = '0 ; role id for role given to winner'

        config['MINIGAME'] = {}
        config['MINIGAME']['ROLEID'] = '0 ; role id to allow minigame playing'

        config['ALIAS'] = {}
        config['ALIAS']['CHANNELID'] = '0 ; channel id hosting alias embeds'

        # Save it locally.
        with open(filename, 'w', encoding='utf-8') as configfile:
            config.write(configfile)
        return Settings(config)

    @staticmethod
    def load_config(guild_id: int) -> Optional['Settings']:
        """Attempts to load the local configuration file into memory."""
        if not os.path.exists("configs"):
            os.makedirs("configs")

        filename = f"configs/{guild_id}.ini"

        # Cannot load a non-existing file.
        if not pathlib.Path(filename).is_file():
            return None

        config = configparser.ConfigParser(inline_comment_prefixes=';')
        config.read(filename)

        # Throw an error if a required section is missing.
        for section in REQUIRED_SECTIONS:
            if not config.has_section(section):
                raise ValueError(
                    f"'{section}' is unset in configuration file.")

        return Settings(config)


class Manager():
    """Manages the Settings database in memory and in storage."""
    _guilds: dict[int, Settings] = {}
    prefix: str = '['

    @staticmethod
    def init(guild_id: int) -> None:
        """Initializes the Settings Manager, loading them from files."""
        try:
            # Load the configuration file.
            config = Settings.load_config(guild_id)
        except BaseException as err:
            Log.error(f"Error while loading configuration file:\n{str(err)}")
            return

        # Create the configuration file if it could not be loaded.
        if not config:
            Log.info(f"Configuration file '{guild_id}' does not exist.")
            if Settings.make_default_config(guild_id):
                Log.info(f"Default config: '{guild_id}' created.")
                return Manager.init(guild_id)
            Log.info(f"Configuration file '{guild_id}' failed to create.")
            return

        Manager.add(config)

    @staticmethod
    def add(setting: Settings) -> Settings:
        """Adds a setting to memory, does not save it to database."""
        Manager._guilds[setting.guild_id] = setting
        return setting

    @staticmethod
    def get(guild_id: int) -> Settings:
        """Get a setting for a guild based on its id. If it does not exist,
        it will be initialized with defaults.
        """
        setting = Manager._guilds.get(guild_id)
        if not setting:
            # Create the settings since it does not exist.
            setting = Settings.make_default_config(guild_id)
            Manager.add(setting)
        return setting
