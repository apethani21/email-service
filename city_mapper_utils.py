import json
import logging as log
import os

import requests

log.basicConfig(level=log.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

base_endpoint = "https://api.external.citymapper.com/api/1"


def _get_citymapper_auth():
    home = os.path.expanduser("~")
    with open(f"{home}/keys/city-mapper/api_key", "r") as f:
        key = f.read().rstrip("\n")
    return {"Citymapper-Partner-Key": key}


def get_location_config(area=None):
    with open(f"./configs/location.json", "r") as f:
        location = json.loads(f.read())
    if area is None:
        return location
    else:
        return location[area]


def get_travel_time(start, end):
    """Response JSON like {"transit_time_minutes": 28}"""

    location_config = get_location_config()
    start_lat = location_config[start]["latitude"]
    start_long = location_config[start]["longitude"]
    end_lat = location_config[end]["latitude"]
    end_long = location_config[end]["longitude"]
    params = {
        "start": f"{start_lat},{start_long}",
        "end": f"{end_lat},{end_long}",
        "traveltime_types": "transit",
    }
    headers = _get_citymapper_auth()
    r = requests.get(
        url=f"{base_endpoint}/traveltimes", params=params, headers=headers, timeout=1
    )
    r.raise_for_status()
    return r.json()


def get_journey_info(**kwargs):
    locations = kwargs["weather"]
    hour_start = 24
    hour_end = 0
    for loc_info in locations:
        if list(loc_info.values())[0] < hour_start:
            start, hour_start = tuple(loc_info.items())[0]
        if list(loc_info.values())[0] > hour_end:
            end, hour_end = tuple(loc_info.items())[0]

    try:
        travel_time = get_travel_time(start, end)
    except requests.exceptions.ReadTimeout:
        log.info("get_travel_time: requests.exceptions.ReadTimeout")
        travel_time = {"transit_time_minutes": None}
    return {"start": start, "end": end, "travel_time": travel_time}
