"""Platform for Mi Temperature and Humidity 2 integration."""
import logging
import pexpect
import voluptuous as vol

from datetime import datetime, timedelta

import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.components.sensor import (
    PLATFORM_SCHEMA,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.const import (
    CONF_MAC,
    CONF_MONITORED_CONDITIONS,
    CONF_NAME,
    CONF_TIMEOUT,
    DEVICE_CLASS_HUMIDITY,
    DEVICE_CLASS_TEMPERATURE,
    PERCENTAGE,
    TEMP_CELSIUS,
)

_LOGGER = logging.getLogger(__name__)

CONF_NAME = 'name'
CONF_MAC = 'mac'
CONF_ADAPTER = 'adapter'
CONF_RETRIES = 'retries'
CONF_TIMEOUT = 'timeout'

DEFAULT_ADAPTER = 'hci0'
DEFAULT_NAME = 'MiTempHumidity'
DEFAULT_TIMEOUT = 10
DEFAULT_RETRIES = 5

_HANDLE_READ_WRITE_SENSOR_DATA = '0x0038', '0100'

SENSOR_TYPES: tuple[SensorEntityDescription] = (
    SensorEntityDescription(
        key="temperature",
        name="Temperature",
        device_class=DEVICE_CLASS_TEMPERATURE,
        native_unit_of_measurement=TEMP_CELSIUS,
    ),
    SensorEntityDescription(
        key="humidity",
        name="Humidity",
        device_class=DEVICE_CLASS_HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
    )
)

SENSOR_KEYS = [desc.key for desc in SENSOR_TYPES]

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_ADAPTER, default=DEFAULT_ADAPTER): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): cv.string,
    vol.Optional(CONF_RETRIES, default=DEFAULT_RETRIES): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_MONITORED_CONDITIONS, default=SENSOR_KEYS): vol.All(
        cv.ensure_list, [vol.In(SENSOR_KEYS)]
    ),
    vol.Required(CONF_MAC): cv.string
})

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Mi Temperature and Humidity 2 platform."""
    add_entities([
        MiTempHumidity(config, sensor)
        for sensor in SENSOR_TYPES
        if sensor.key in config[CONF_MONITORED_CONDITIONS]
    ])

class MiTempHumidity(SensorEntity):
    """Representation of an Mi Temperature and Humidity 2 sensor."""

    def __init__(self, config, sensor):
        """Initialize the sensor."""
        self._prefix = config['name']
        self._mac = config['mac']
        self._adapter = config['adapter']
        self._timeout = int(config['timeout'])
        self._retries = int(config['retries'])
        self._sensor = sensor

        self._cache_timeout = timedelta(seconds=600)
        self._cache_data = {}
        self._last_read = None

        self._gatt = pexpect.spawn(f'gatttool -i {self._adapter} -b {self._mac} -I')

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return f'{self._prefix}_{self._sensor.key}'

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._cache_data.get(self._sensor.key, 0)
    
    @property
    def unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return self._sensor.native_unit_of_measurement

    def update(self):
        """Update data."""
        if not self._last_read or (datetime.now() - self._cache_timeout) > self._last_read:
            data = None
            retry = 0

            while data == None and retry < self._retries:
                try:
                    data = self._get_sensor_data(
                        _HANDLE_READ_WRITE_SENSOR_DATA[0],
                        _HANDLE_READ_WRITE_SENSOR_DATA[1]
                    )
                    self._cache_data = data
                except pexpect.exceptions.TIMEOUT: 
                    _LOGGER.debug(f'Timed out, retry {retry}.')
                    retry += 1
            self._last_read = datetime.now()
        else:
            _LOGGER.debug(
                f'Using cache ({datetime.now() - self._last_read} < {self._cache_timeout})'
            )

        _LOGGER.debug(f'{self._prefix}_{self._sensor.key} = {self._cache_data}')
    
    def _get_sensor_data(self, handle, value):
        self._gatt.sendline('connect')
        self._gatt.expect('Connection successful', timeout = self._timeout)
        self._gatt.sendline(f'char-write-req {handle} {value}')
        self._gatt.expect('Characteristic value was written successfully')
        self._gatt.expect('Notification handle = 0x0036 value: ')
        self._gatt.expect("\r\n")
        sensor_data = self._gatt.before.decode().split(' ')
        self._gatt.sendline('disconnect')

        return  {
            'temperature': int(f'{sensor_data[1]}{sensor_data[0]}', 16)/100,
            'humidity': int(f'{sensor_data[2]}', 16)
        }
