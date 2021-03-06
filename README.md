[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)

# NIWA Tides integeration for Home Assistant

Custom integration for Home Assistant to get New Zealand tide information from NIWA Tides API.

# Setup

## Get API Key for NIWA Tide API

1. Sign-up at https://developer.niwa.co.nz/
2. Add a new app on https://developer.niwa.co.nz/my-apps
3. Get the API Key for the new app

## Home Assistant Configuration

```yaml
sensor:
  - platform: niwa_tides
    api_key: !secret niwa_tides_api_key
    entity_id: "local_tides"
    name: Local Tides
```

# Sensor

The sensor provides current tide level (in meters). Sensor updates its state every 5 minutes, calculating the level from low and high levels obtained from the API. The API call is only made once every change of tide.

The sensor also provides additional data via attributes:

| Attribute             | Example             | Description  |
| :-------------------- | :------------------ | :----------- |
| `last_tide_level`     | 1.03                | height of the tide (high or low) immediately preceeding current time.
| `last_tide_time`      | 2021-02-21T09:07:00 | time of the tide (high or low) immediately preceeding current time.
| `last_tide_hours`     | 1.2                 | number of hours since last tide (high or low).
| `next_tide_level`     | 2.64                | height of the tide (high or low) immediately following current time.
| `next_tide_time`      | 2021-02-21T15:14:00 | time of the tide (high or low) immediately following current time.
| `next_tide_hours`     | 4.9                 | number of hours until next tide (high or low).
| `next_high_tide_level`| 2.64                | height of the high tide immediately following current time.
| `next_high_tide_time` | 2021-02-21T15:14:00 | time of the high tide immediately following current time.
| `next_high_tide_hours`| 4.9                 | number of hours until next high tide.
| `next_low_tide_level` | 0.86                | height of the low tide immediately following current time.
| `next_low_tide_time`  | 2021-02-21T21:34:00 | time of the low tide immediately following current time.
| `next_low_tide_hours` | 11.1                | number of hours until next low tide.
| `tide_percent`        | 18                  | current tide leve in percentages (%0 = low tide, 100% = high tide).
| `tide_phase`          | increasing          | current phase of the tide with possible values: `low` (<5%), `increasing`, `high` (>95%), `decreasing`.

