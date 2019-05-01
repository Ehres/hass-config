"""Load RF Player integration."""
DOMAIN = 'rfplayer'

def setup(hass, config):
    """RF Player controller/hub specific code."""

    hass.helpers.discovery.load_platform('cover', DOMAIN, {}, config)

    return True