"""Version information for ocpp2mqtt."""

__version__ = "1.0b"
__version_info__ = (1, 0, "beta")

# Application metadata
APP_NAME = "ocpp2mqtt"
APP_DESCRIPTION = "OCPP to MQTT Gateway for EV Charging Stations"
APP_AUTHOR = "gyzod"
APP_URL = "https://github.com/gyzod/ocpp2mqtt"


def get_version_string() -> str:
    """Return formatted version string for display."""
    return f"{APP_NAME} v{__version__}"


def get_banner() -> str:
    """Return startup banner with version info."""
    return f"""
════════════════════════════════════════════════════════════════════════════════════
    ______
   /|_||_\\`.__
  (   _    _ _\\c--[⚡]
  `-(_)--(_)-'

  {APP_NAME.upper()} - OCPP to MQTT Gateway              
  Version: {__version__:<44}
  {APP_URL:<52}
════════════════════════════════════════════════════════════════════════════════════

"""
