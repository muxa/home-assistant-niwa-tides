"""Support for the NIWA Tides API."""
from datetime import timedelta
import logging
import time
import datetime

import math

import requests
import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    CONF_API_KEY,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_NAME,
    CONF_ENTITY_ID,
    LENGTH_METERS
)
import homeassistant.helpers.config_validation as cv
# from homeassistant.helpers.entity import Entity
from homeassistant.helpers.restore_state import RestoreEntity

_LOGGER = logging.getLogger(__name__)

ATTRIBUTION = "Data provided by NIWA"
DEFAULT_NAME = "NIWA Tides"
DEFAULT_ENTITY_ID = "niwa_tides"
ICON = "mdi:waves"
ATTR_LAST_TIDE_LEVEL = "last_tide_level"
ATTR_LAST_TIDE_TIME = "last_tide_time"
ATTR_LAST_TIDE_HOURS = "last_tide_hours"
ATTR_NEXT_TIDE_LEVEL = "next_tide_level"
ATTR_NEXT_TIDE_TIME = "next_tide_time"
ATTR_NEXT_TIDE_HOURS = "next_tide_hours"
ATTR_NEXT_HIGH_TIDE_LEVEL = "next_high_tide_level"
ATTR_NEXT_HIGH_TIDE_TIME = "next_high_tide_time"
ATTR_NEXT_HIGH_TIDE_HOURS = "next_high_tide_hours"
ATTR_NEXT_LOW_TIDE_LEVEL = "next_low_tide_level"
ATTR_NEXT_LOW_TIDE_TIME = "next_low_tide_time"
ATTR_NEXT_LOW_TIDE_HOURS = "next_low_tide_hours"
ATTR_TIDE_PERCENT = "tide_percent"
ATTR_TIDE_PHASE = "tide_phase"

SCAN_INTERVAL = timedelta(seconds=300) # every 5 minutes

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_API_KEY): cv.string,
        vol.Optional(CONF_LATITUDE): cv.latitude,
        vol.Optional(CONF_LONGITUDE): cv.longitude,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_ENTITY_ID, default=DEFAULT_ENTITY_ID): cv.string,
    }
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the NiwaTidesInfo sensor."""
    name = config.get(CONF_NAME)
    entity_id = config[CONF_ENTITY_ID]
    lat = config.get(CONF_LATITUDE, hass.config.latitude)
    lon = config.get(CONF_LONGITUDE, hass.config.longitude)
    key = config.get(CONF_API_KEY)

    if None in (lat, lon):
        _LOGGER.error("Latitude or longitude not set in Home Assistant config")

    tides = NiwaTidesInfoSensor(name, entity_id, lat, lon, key)
    tides.update()
    if tides.data == None:
        _LOGGER.error("Unable to retrieve tides data")
        return

    add_entities([tides])


class NiwaTidesInfoSensor(RestoreEntity):
    """Representation of a NiwaTidesInfo sensor."""

    def __init__(self, name, entity_id, lat, lon, key):
        """Initialize the sensor."""
        self._name = name
        self._entity_id = entity_id
        self._lat = lat
        self._lon = lon
        self._key = key
        self.data = None
        self.tide_percent = None
        self.current_tide_level = None
        self.last_tide = None
        self.next_tide = None
        self.next_high_tide = None
        self.next_low_tide = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def unique_id(self):
        """Return the unique ID of the sensor."""
        return self._entity_id

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.data != None

    @property
    def icon(self):
        """Return sensor icon."""
        return ICON
    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return LENGTH_METERS

    @property
    def device_state_attributes(self):
        """Return the state attributes of this device."""
        if self.last_update_at == None:
            self.last_update_at = datetime.datetime.now()

        attr = {
            ATTR_ATTRIBUTION: ATTRIBUTION,
            ATTR_LAST_TIDE_LEVEL: self.last_tide.value if self.last_tide is not None else None,
            ATTR_LAST_TIDE_TIME: self.last_tide.time if self.last_tide is not None else None,
            ATTR_LAST_TIDE_HOURS: difference_in_hours(self.last_tide.time, self.last_update_at) if self.last_tide is not None else None,
            ATTR_NEXT_TIDE_LEVEL: self.next_tide.value if self.next_tide is not None else None,
            ATTR_NEXT_TIDE_TIME: self.next_tide.time if self.next_tide is not None else None,
            ATTR_NEXT_TIDE_HOURS: difference_in_hours(self.last_update_at, self.next_tide.time) if self.next_tide is not None else None,
            ATTR_NEXT_HIGH_TIDE_LEVEL: self.next_high_tide.value if self.next_high_tide is not None else None,
            ATTR_NEXT_HIGH_TIDE_TIME: self.next_high_tide.time if self.next_high_tide is not None else None,
            ATTR_NEXT_HIGH_TIDE_HOURS: difference_in_hours(self.last_update_at, self.next_high_tide.time) if self.next_high_tide is not None else None,
            ATTR_NEXT_LOW_TIDE_LEVEL: self.next_low_tide.value if self.next_low_tide is not None else None,
            ATTR_NEXT_LOW_TIDE_TIME: self.next_low_tide.time if self.next_low_tide is not None else None,
            ATTR_NEXT_LOW_TIDE_HOURS: difference_in_hours(self.last_update_at, self.next_low_tide.time) if self.next_low_tide is not None else None,
            ATTR_TIDE_PERCENT: self.tide_percent,
            ATTR_TIDE_PHASE: self.tide_phase
        }
        return attr

    @property
    def state(self):
        """Return the state of the device."""
        return self.current_tide_level
        
    def update(self):
        """Get the latest data from NIWA Tides API or calculate."""

        self.last_update_at = datetime.datetime.now()

        if self.data == None or self.next_tide == None or datetime.datetime.now() > self.next_tide.time:
            # never updated, or it's time to get next tide info            
            start = datetime.date.fromtimestamp(time.time()).isoformat()
            _LOGGER.info("Fetching tide data for %s", start)
            resource = (
                "https://api.niwa.co.nz/tides/data?lat={}&long={}&numberOfDays=2&startDate={}"
            ).format(self._lat, self._lon, start)

            try:
                req = requests.get(resource, timeout=10, headers = {"x-apikey": self._key})
                self.data = req.json()
                req.close()
                
                _LOGGER.debug("Data: %s", self.data)

                self.calculate_tide()
            except ValueError as err:
                _LOGGER.error("Error retrieving data from NIWA tides API: %s", err.args)
                _LOGGER.debug("Response (%s): %s", req.status_code, req.text)
                self.data = None
        else:
            # we can simply calculate the tide from existing data
            self.calculate_tide()

    def calculate_tide(self):
        if self.data:
            t = datetime.datetime.now()

            last_tide = None # the time and height of the tide (high or low) immediately preceeding current time
            next_tide = None # the time and height of the tide (high or low) immediately following current time
            next_high_tide = None # the time and height of the high tide immediately following current time
            next_low_tide = None # the time and height of the low tide immediately following current time

            for value in self.data["values"]:
                # parse date and convert from UTC to local                
                parsed_time = datetime.datetime.strptime(value["time"], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=datetime.timezone.utc).astimezone().replace(tzinfo=None)
                if next_tide == None:
                    # we have not found next tide yet
                    if parsed_time > t:
                        # we found next tide
                        next_tide = TideInfo(parsed_time, value["value"])

                        if next_tide.value > last_tide.value:
                            # next tide is high
                            next_high_tide = next_tide
                        else:
                            # next tide is low
                            next_low_tide = next_tide
                    else:
                        # this might be the last tide
                        last_tide = TideInfo(parsed_time, value["value"])
                else:
                    # this is the tide following next one
                    # figure out if it will be high or low
                    if next_high_tide == None:
                        next_high_tide = TideInfo(parsed_time, value["value"])
                    else:
                        next_low_tide = TideInfo(parsed_time, value["value"])
                    # we are done
                    break

            # now can calculate current level
            tide_ratio = (1-math.cos(math.pi*(t-last_tide.time)/(next_tide.time-last_tide.time)))/2
            h = last_tide.value + (next_tide.value - last_tide.value)*tide_ratio
            h = round(h, 2)

            _LOGGER.debug("Current tide: %s. Last tide: %s. Next tide: %s", h, last_tide, next_tide)
            _LOGGER.debug("Next high tide: %s. Next low tide: %s", next_high_tide, next_low_tide)

            if last_tide.value > next_tide.value:
                # tide is decreasing
                tide_ratio = 1 - tide_ratio

            self.tide_percent = round(tide_ratio * 100, 0)
            self.current_tide_level = h
            self.last_tide = last_tide
            self.next_tide = next_tide
            self.next_high_tide = next_high_tide
            self.next_low_tide = next_low_tide

            if self.tide_percent < 5:
                self.tide_phase = "low"
            elif self.tide_percent > 95:
                self.tide_phase = "high"
            elif last_tide.value < next_tide.value:
                self.tide_phase = "increasing"
            else:
                self.tide_phase = "decreasing"

        else:
            self.tide_percent = None
            self.current_tide_level = None
            self.last_tide = None
            self.next_tide = None
            self.next_high_tide = None
            self.next_low_tide = None

class TideInfo:
    def __init__(self, time: datetime.datetime, value: float):
        self.time = time
        self.value = value

    def __str__(self):
        return f'{self.value}m at {self.time}'


def difference_in_hours(earlier_time, later_time):        
    diff = later_time - earlier_time
    return round(diff.days*24 + diff.seconds/3600, 1)