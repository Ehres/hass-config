"""my first component."""
import asyncio
import logging

from datetime import timedelta

try:
    from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
    from homeassistant.const import (
        CONF_SCAN_INTERVAL,
        EVENT_HOMEASSISTANT_STARTED,
    )
    from homeassistant.core import CoreState, callback
    from homeassistant.exceptions import ConfigEntryNotReady
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.typing import ConfigType

    from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
except ImportError:
    # si py test
    class DataUpdateCoordinator:
        def __init__(self):
            # nothing to do
            pass
    class ConfigEntryNotReady:
        def __init__(self):
            # nothing to do
            pass
    class HomeAssistant:
        def __init__(self):
            # nothing to do
            pass
    class ConfigType:
        def __init__(self):
            # nothing to do
            pass
    class SOURCE_IMPORT:
        def __init__(self):
            # nothing to do
            pass
    class ConfigEntry:
        def __init__(self):
            # nothing to do
            pass
    class callback:
        def __init__(self):
            # nothing to do
            pass



from . import myClientEnedis

from .const import (
    CONF_TOKEN,
    CONF_CODE,
    DOMAIN,
    PLATFORM,
    HP_COST,
    HC_COST,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SENSOR_INTERVAL,
    myENEDIS_SERVICE,
    __VERSION__,
    __name__,
    CONF_DELAY,
    HEURESCREUSES_ON,
    HEURES_CREUSES,
    UNDO_UPDATE_LISTENER,
    COORDINATOR_ENEDIS,
    PLATFORMS,
    DEFAULT_REPRISE_ERR,
)


_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(hours=3, minutes=00) # delai de lancement pour savoir si update à faire

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up Enedis from legacy config file."""
    conf = config.get(DOMAIN)
    if not conf:
        return True

    for enedis_conf in conf:
        ch = dir(enedis_conf)
        _LOGGER.info("enedis_conf data %s" %ch)
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": SOURCE_IMPORT}, data=enedis_conf
            )
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up an Enedis account from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    heurescreuses = entry.options.get(HEURES_CREUSES, None)
    if ( heurescreuses == "" ): heurescreuses = None
    _LOGGER.info("**enedis**_conf heurescreuses *%s*" % heurescreuses)
    #heurescreuses = None
    delai_interval = entry.options.get(SCAN_INTERVAL)
    token = entry.options.get(CONF_TOKEN, "")
    code = str(entry.options.get(CONF_CODE, ""))
    hpcost = float(entry.options.get(HP_COST, "0.0"))
    hccost = float(entry.options.get(HC_COST, "0.0"))
    heurescreusesON = bool(entry.options.get(HEURESCREUSES_ON, True)),

    client = myClientEnedis.myClientEnedis(token, code, delai=DEFAULT_REPRISE_ERR,
                                       heuresCreuses=heurescreuses, heuresCreusesCost=hccost,
                                       heuresPleinesCost=hpcost,
                                       version=__VERSION__, heuresCreusesON=heurescreusesON)

    coordinator_enedis = sensorEnedisCoordinator(hass, entry, client)

    await coordinator_enedis.async_setup()
    async def _enable_scheduled_myEnedis(*_):
        """Activate the data update coordinator."""
        coordinator_enedis.update_interval = timedelta(seconds=DEFAULT_SCAN_INTERVAL        )
        await coordinator_enedis.async_refresh()

    if hass.state == CoreState.running:
        await _enable_scheduled_myEnedis()
        if not coordinator_enedis.last_update_success:
            raise ConfigEntryNotReady

    else:
        # Running a speed test during startup can prevent
        # integrations from being able to setup
        hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STARTED, _enable_scheduled_myEnedis
        )

    undo_listener = entry.add_update_listener(_async_update_listener)
    hass.data[DOMAIN][entry.entry_id] = {
        COORDINATOR_ENEDIS: coordinator_enedis,
        UNDO_UPDATE_LISTENER: undo_listener,
    }

    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, platform)
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, platform)
                for platform in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN][entry.entry_id][UNDO_UPDATE_LISTENER]()
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)

    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)

class sensorEnedisCoordinator(DataUpdateCoordinator):

    def __init__(self, hass, entry, client):
        """Initialize the data object."""
        self.hass = hass
        self.entry = entry
        self.clientEnedis = client
        async def _async_update_data_enedis():
            """Fetch data from API endpoint."""
            return await hass.async_add_executor_job(
                self.clientEnedis.getData
        )
        super().__init__(
            self.hass,
            _LOGGER,
            name=f"Enedis information for {entry.title}",
            update_method=_async_update_data_enedis,
            update_interval=SCAN_INTERVAL,
        )

    async def async_set_options(self):
        """Set options for entry."""
        _LOGGER.info("async_set_options - proc -- %s" % self.entry.options)
        if not self.entry.options:
            _LOGGER.info(".config_entry.options()")
            data = {**self.entry.data}
            options = {
                CONF_SCAN_INTERVAL: data.pop(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                CONF_TOKEN: data.pop(CONF_TOKEN, ""),
                CONF_CODE: str(data.pop(CONF_CODE, "")),
                HP_COST: str(data.pop(HP_COST, "0.0")),
                HC_COST: str(data.pop(HC_COST, "0.0")),
                HEURESCREUSES_ON: bool(data.pop(HEURESCREUSES_ON, True)),
                HEURES_CREUSES: str(data.pop(HEURES_CREUSES, "[]")),
            }
            self.hass.config_entries.async_update_entry(
                self.entry, data=data, options=options
            )
            _LOGGER.info(".config_entry.options() - done")
        _LOGGER.info("async_set_options - proc -- done ")

    def update_OptionsMyEnedis(self):
        _LOGGER.info("update_MyEnedis pre-getini for %s" % (self.entry.options['token']))
        _LOGGER.info("getInit()")
        hccost = float(self.entry.options.get(HC_COST, "0.0"))
        hpcost = float(self.entry.options.get(HP_COST, "0.0"))
        token, code = self.entry.options[CONF_TOKEN], self.entry.options[CONF_CODE]
        heurescreusesON = self.entry.options[HEURESCREUSES_ON]
        heurescreusesch = self.entry.options.get(HEURES_CREUSES, "[]")
        if ( heurescreusesch == "" ):
            heurescreusesch = "[]"
        heurescreuses = eval(heurescreusesch)
        _LOGGER.info("options - proc -- %s %s %s %s %s %s" % (token, code, hccost, hpcost, heurescreusesON, heurescreuses))

        self.clientEnedis = myClientEnedis.myClientEnedis(token, code, delai=DEFAULT_REPRISE_ERR,
                                           heuresCreuses=heurescreuses, heuresCreusesCost=hccost,
                                           heuresPleinesCost=hpcost,
                                           version=__VERSION__, heuresCreusesON=heurescreusesON)

    async def async_setup(self):
        #Set up myEnedis.
        try:
            _LOGGER.info("run my First Extension")
            # ne sert plus normalement ...
            # self.myEnedis = await self.hass.async_add_executor_job(self.clientEnedis.getData)
            _LOGGER.info("run my First Extension - done -- ")
        except Exception as inst:
            raise Exception(inst)

        async def request_update(call):
            # Request update.
            await self.async_request_refresh()

        #await self.async_set_options()
        #await self.hass.async_add_executor_job(self.clientEnedis.getData)
        await self.async_set_options()
        await self.hass.async_add_executor_job(self.update_OptionsMyEnedis)
        self._unsub_update_listener = self.entry.add_update_listener(
            options_updated_listener
        )
        """ """


async def options_updated_listener(hass, entry):
    """Handle options update. suite modification options"""
    _LOGGER.info("options_updated_listener ")
    #hass.data[DOMAIN][entry.entry_id].update_interval = timedelta(seconds=DEFAULT_SENSOR_INTERVAL)
    #await hass.data[DOMAIN][entry.entry_id].async_request_refresh()
    _LOGGER.info("options_updated_listener - done -- ")