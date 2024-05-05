"""Platform for Mi Temperature and Humidity 2 integration."""
import logging
import os
import voluptuous as vol

from datetime import datetime, timedelta

import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.components.sensor import (
    PLATFORM_SCHEMA,
    SensorEntity,
    SensorEntityDescription,
    SensorDeviceClass,
)
from homeassistant.const import (
    CONF_MAC,
    CONF_MONITORED_CONDITIONS,
    CONF_NAME,
    PERCENTAGE,
)

from homeassistant.const import UnitOfTemperature

_LOGGER = logging.getLogger(__name__)

CONF_NAME = "name"
CONF_MAC = "mac"
CONF_ADAPTER = "adapter"

DEFAULT_ADAPTER = "hci0"
DEFAULT_NAME = "MiTempHumidity"

HANDLE_DATA = "0x0033", "0100"
SCAN_INTERVAL = timedelta(minutes=5)

SENSOR_TYPES: tuple[SensorEntityDescription] = (
    SensorEntityDescription(
        key="temperature",
        name="Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    SensorEntityDescription(
        key="humidity",
        name="Humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
    )
)

SENSOR_KEYS = [desc.key for desc in SENSOR_TYPES]

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_ADAPTER, default=DEFAULT_ADAPTER): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_MONITORED_CONDITIONS, default=SENSOR_KEYS): vol.All(
        cv.ensure_list, [vol.In(SENSOR_KEYS)]
    ),
    vol.Required(CONF_MAC): cv.string
})

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Mi Temperature and Humidity 2 platform."""
    async_add_entities([
        MiTempHumidity(config, sensor)
        for sensor in SENSOR_TYPES
        if sensor.key in config[CONF_MONITORED_CONDITIONS]
    ])

class MiTempHumidity(SensorEntity):
    """Representation of an Mi Temperature and Humidity 2 sensor."""

    def __init__(self, config, sensor):
        """Initialize the sensor."""
        self._prefix = config["name"]
        self._mac = config["mac"]
        self._adapter = config["adapter"]
        self._sensor = sensor
        self._data = {}

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return f"{self._prefix}_{self._sensor.key}"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._data.get(self._sensor.key, 0)
    
    @property
    def unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return self._sensor.native_unit_of_measurement

    async def async_update(self):
        """Update data."""
        results = os.popen(
            f"gatttool -i {self._adapter} -b {self._mac} --char-read --handle={HANDLE_DATA[0]} --value={HANDLE_DATA[1]}",
            mode="r"
        )
        sensor_data = results.read()
        
        if not results.close():
            sensor_data = sensor_data.split(":")
            if len(sensor_data) == 2:
                sensor_data = sensor_data[1].strip().split(" ")

                self._data = {
                    "temperature": int(f"{sensor_data[1]}{sensor_data[0]}", 16)/100,
                    "humidity": int(f"{sensor_data[2]}", 16)
                }
        return self._data
