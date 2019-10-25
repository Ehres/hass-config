import logging

import voluptuous as vol

# Import the device class from the component that you want to support
from homeassistant.components.cover import (
  CoverDevice, SUPPORT_OPEN, SUPPORT_CLOSE, ATTR_POSITION,
    ATTR_TILT_POSITION, PLATFORM_SCHEMA)
# from homeassistant.const import CONF_HOST, CONF_USERNAME, CONF_PASSWORD
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.event import track_utc_time_change

# Home Assistant depends on 3rd party packages for API specific code.
REQUIREMENTS = ['pyserial==3.1.1']

_LOGGER = logging.getLogger(__name__)

# Validation of the rfplayer's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required('port'): cv.string,
})

OPEN_COMMAND='ON'
CLOSE_COMMAND='OFF'

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the Rfplayer X2D Covers platform."""
    import serial

    # Assign configuration variables. The configuration check takes care they are
    # present.
    # port = config.get('port')
    port = '/dev/ttyUSB0'
    # devices = config.get('entities')
    devices = [
        {
            'name': 'bar',
            'code': 'A1'
        },
        {
            'name': 'dining_room',
            'code': 'A2'
        },
        {
            'name': 'living_room',
            'code': 'A3'
        },
        {
            'name': 'kitchen',
            'invert': True,
            'code': 'A4'
        },
        {
            'name': 'bedroom',
            'code': 'A5'
        },
        {
            'name': 'mezzanine',
            'code': 'A6'
        },
        {
            'name': 'louis_bedroom',
            'code': 'A7'
        }
    ]

    # Setup connection with rfplayer
    hub = serial.Serial(port, 115200)
    print(hub)

    # Verify that passed in configuration works
    if not hub.is_open:
        _LOGGER.error("Could not connect to RFPlayer hub")
        return


    #invert = 'invert' in device and device['invert'] or False
    # Add devices
    add_devices(RFPlayer(hass, hub, device['name'], device['code'], 'invert' in device and device['invert'] or False, position=0, supported_features=(SUPPORT_OPEN | SUPPORT_CLOSE)) for device in devices)



class RFPlayer(CoverDevice):
    """Representation of an RFPlayer X2D Cover."""

    def __init__(self, hass, hub, name, code, is_invert=False, position=None, tilt_position=None, device_class=None, supported_features=None):
        """Initialize the cover."""
        self.hass = hass
        self.hub = hub
        self._name = name
        self._code = code
        self._is_invert = is_invert
        self._position = position
        self._device_class = device_class
        self._supported_features = supported_features
        self._set_position = None
        self._set_tilt_position = None
        self._tilt_position = tilt_position
        self._requested_closing = True
        self._requested_closing_tilt = True
        self._unsub_listener_cover = None
        self._unsub_listener_cover_tilt = None
        self._is_opening = False
        self._is_closing = False
        if position is None:
            self._closed = True
        else:
            self._closed = self.current_cover_position <= 0

    @property
    def name(self):
        """Return the name of the cover."""
        return self._name

    @property
    def should_poll(self):
        """No polling needed for a rfplayer cover."""
        return False

    @property
    def current_cover_position(self):
        """Return the current position of the cover."""
        return self._position

    @property
    def current_cover_tilt_position(self):
        """Return the current tilt position of the cover."""
        return self._tilt_position

    @property
    def is_closed(self):
        """Return if the cover is closed."""
        return self._closed

    @property
    def is_closing(self):
        """Return if the cover is closing."""
        return self._is_closing

    @property
    def is_opening(self):
        """Return if the cover is opening."""
        return self._is_opening

    @property
    def device_class(self):
        """Return the class of this device, from component DEVICE_CLASSES."""
        return self._device_class

    @property
    def supported_features(self):
        """Flag supported features."""
        if self._supported_features is not None:
            return self._supported_features
        return super().supported_features

    def close_cover(self, **kwargs):
        """Close the cover."""
        command = self._is_invert and 'ON' or 'OFF'
        full_command = [ord(c) for c in 'ZIA++{command} {code} X2DSHUTTER\n\r'.format(code=self._code, command=command)]
        self.hub.write(full_command)

        if self._position == 0:
            return
        if self._position is None:
            self._closed = True
            self.schedule_update_ha_state()
            return

        self._is_closing = True
        self._listen_cover()
        self._requested_closing = True
        self.schedule_update_ha_state()

    def close_cover_tilt(self, **kwargs):
        """Close the cover tilt."""
        if self._tilt_position in (0, None):
            return

        self._listen_cover_tilt()
        self._requested_closing_tilt = True

    def open_cover(self, **kwargs):
        """Open the cover."""
        command = self._is_invert and 'OFF' or 'ON'
        full_command = [ord(c) for c in 'ZIA++{command} {code} X2DSHUTTER\n\r'.format(code=self._code, command=command)]
        self.hub.write(full_command)

        if self._position == 100:
            return
        if self._position is None:
            self._closed = False
            self.schedule_update_ha_state()
            return

        self._is_opening = True
        self._listen_cover()
        self._requested_closing = False
        self.schedule_update_ha_state()

    def open_cover_tilt(self, **kwargs):
        """Open the cover tilt."""
        if self._tilt_position in (100, None):
            return

        self._listen_cover_tilt()
        self._requested_closing_tilt = False

    def set_cover_position(self, **kwargs):
        """Move the cover to a specific position."""
        position = kwargs.get(ATTR_POSITION)
        self._set_position = round(position, -1)
        if self._position == position:
            return

        self._listen_cover()
        self._requested_closing = position < self._position

    def set_cover_tilt_position(self, **kwargs):
        """Move the cover til to a specific position."""
        tilt_position = kwargs.get(ATTR_TILT_POSITION)
        self._set_tilt_position = round(tilt_position, -1)
        if self._tilt_position == tilt_position:
            return

        self._listen_cover_tilt()
        self._requested_closing_tilt = tilt_position < self._tilt_position

    def stop_cover(self, **kwargs):
        """Stop the cover."""
        self._is_closing = False
        self._is_opening = False
        if self._position is None:
            return
        if self._unsub_listener_cover is not None:
            self._unsub_listener_cover()
            self._unsub_listener_cover = None
            self._set_position = None

    def stop_cover_tilt(self, **kwargs):
        """Stop the cover tilt."""
        if self._tilt_position is None:
            return

        if self._unsub_listener_cover_tilt is not None:
            self._unsub_listener_cover_tilt()
            self._unsub_listener_cover_tilt = None
            self._set_tilt_position = None

    def _listen_cover(self):
        """Listen for changes in cover."""
        if self._unsub_listener_cover is None:
            self._unsub_listener_cover = track_utc_time_change(
                self.hass, self._time_changed_cover)

    def _time_changed_cover(self, now):
        """Track time changes."""
        if self._requested_closing:
            self._position -= 10
        else:
            self._position += 10

        if self._position in (100, 0, self._set_position):
            self.stop_cover()

        self._closed = self.current_cover_position <= 0

        self.schedule_update_ha_state()

    def _listen_cover_tilt(self):
        """Listen for changes in cover tilt."""
        if self._unsub_listener_cover_tilt is None:
            self._unsub_listener_cover_tilt = track_utc_time_change(
                self.hass, self._time_changed_cover_tilt)

    def _time_changed_cover_tilt(self, now):
        """Track time changes."""
        if self._requested_closing_tilt:
            self._tilt_position -= 10
        else:
            self._tilt_position += 10

        if self._tilt_position in (100, 0, self._set_tilt_position):
            self.stop_cover_tilt()

        self.schedule_update_ha_state()
