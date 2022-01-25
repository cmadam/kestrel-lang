import os
import json
import logging

from kestrel.config import (
    CONFIG_DIR_DEFAULT,
    load_user_config,
)
from kestrel.utils import update_nested_dict
from kestrel.exceptions import InvalidConfiguration, InvalidDataSource

PROFILE_PATH_DEFAULT = CONFIG_DIR_DEFAULT / "stixshifter.yaml"
PROFILE_PATH_ENV_VAR = "KESTREL_STIXSHIFTER_CONFIG"
STIXSHIFTER_DEBUG_ENV_VAR = "KESTREL_STIXSHIFTER_DEBUG"  # debug mode for stix-shifter if the environment variable exists
ENV_VAR_PREFIX = "STIXSHIFTER_"
RETRIEVAL_BATCH_SIZE = 512

_logger = logging.getLogger(__name__)

def set_stixshifter_logging_level():
    debug_mode = os.getenv(STIXSHIFTER_DEBUG_ENV_VAR, False)
    logging_level = logging.DEBUG if debug_mode else logging.INFO
    _logger.debug(f"set stix-shifter logging level: {logging_level}")
    logging.getLogger("stix_shifter").setLevel(logging_level)
    logging.getLogger("stix_shifter_utils").setLevel(logging_level)
    logging.getLogger("stix_shifter_modules").setLevel(logging_level)


def load_profiles_from_env_var():
    env_vars = os.environ.keys()
    stixshifter_vars = filter(lambda x: x.startswith(ENV_VAR_PREFIX), env_vars)
    profiles = {}
    for evar in stixshifter_vars:
        items = evar.lower().split("_")
        suffix = items[-1]
        profile = "_".join(items[1:-1])
        _logger.debug(f"processing stix-shifter env var: {evar}:")
        if profile not in profiles:
            profiles[profile] = {}

        # decoding JSON or string values from environment variables
        if suffix == "connection" or suffix == "config":
            try:
                value = json.loads(os.environ[evar])
            except json.decoder.JSONDecodeError:
                raise InvalidDataSource(
                    profile,
                    "stixshifter",
                    f"invalid JSON in {evar} environment variable",
                )
        else:
            value = os.environ[evar]

        _logger.debug(f"profile: {profile}, suffix: {suffix}, value: {value}")
        profiles[profile][suffix] = value

    return profiles


def get_datasource_from_profiles(profile_name, profiles):
    """Validate profile data

    Validate profile data. The data should be a dict with "connector",
    "connection", "config" keys, and appropriate values.

    Args:
        profile_name (str): The name of the profile.
        profiles (dict): name to profile (dict) mapping.

    Returns:
        Bool
    """
    if profile_name not in profiles:
        raise InvalidDataSource(
            profile_name,
            "stixshifter",
            f"no {profile_name} configuration found",
        )
    else:
        profile = profiles[profile_name]
        _logger.debug(f"profile to use: {profile}")
        if "connector" not in profile:
            raise InvalidDataSource(
                profile_name,
                "stixshifter",
                f"no {profile_name} connector defined",
            )
        else:
            connector_name = profile["connector"]
        if "connection" not in profile:
            raise InvalidDataSource(
                profile_name,
                "stixshifter",
                f"no {profile_name} connection defined",
            )
        else:
            connection = profile["connection"]
        if "config" not in profile:
            raise InvalidDataSource(
                profile_name,
                "stixshifter",
                f"no {profile_name} configuration defined",
            )
        else:
            configuration = profile["config"]
        if "host" not in connection:
            raise InvalidDataSource(
                profile_name,
                "stixshifter",
                f'invalid {profile_name} connection section: no "host" field',
            )

        if "port" not in connection and connector_name != "stix_bundle":
            raise InvalidDataSource(
                profile_name,
                "stixshifter",
                f'invalid {profile_name} connection section: no "port" field',
            )

        if "auth" not in configuration:
            raise InvalidDataSource(
                profile_name,
                "stixshifter",
                f'invalid {profile_name} configuration section: no "auth" field',
            )
    return connector_name, connection, configuration


def load_profiles():
    config = load_user_config(PROFILE_PATH_ENV_VAR, PROFILE_PATH_DEFAULT)
    if config and "profiles" in config:
        _logger.debug(f"stix-shifter profiles found in config file")
        profiles_from_file = config["profiles"]
    else:
        _logger.debug("either config file does not exist or no stix-shifter profile found in config file. This may indicate a config syntax error if config file exists.")
        profiles_from_file = {}
    profiles_from_env_var = load_profiles_from_env_var()
    profiles = update_nested_dict(profiles_from_file, profiles_from_env_var)
    _logger.debug(f"profiles loaded: {profiles}")
    return profiles
