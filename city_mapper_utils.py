import datetime
import json
import logging as lgg
import os

import pytz
import requests

lgg.basicConfig(level=lgg.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

base_endpoint = "https://developer.citymapper.com/api/1"


def _get_citymapper_auth():
    home = os.path.expanduser("~")
    with open(f"{home}/keys/city-mapper/api_key", "r") as f:
        key = f.read().rstrip("\n")
    return {"key": key}


def get_location_config(area=None):
    with open(f"./configs/location.json", "r") as f:
        location = json.loads(f.read())
    if area is None:
        return location
    else:
        return location[area]


def get_travel_time(start, end, arrival_time):
    """Response JSON like {'travel_time_minutes': 28}"""

    location_config = get_location_config()
    start_lat = location_config[start]["latitude"]
    start_long = location_config[start]["longitude"]
    end_lat = location_config[end]["latitude"]
    end_long = location_config[end]["longitude"]
    params = {
        "startcoord": f"{start_lat},{start_long}",
        "endcoord": f"{end_lat},{end_long}",
        "time": arrival_time,
        **_get_citymapper_auth(),
    }
    r = requests.get(url=f"{base_endpoint}/traveltime", params=params, timeout=1)
    r.raise_for_status()
    return r.json()


def get_single_point_coverage(location):
    """
    Response JSON like
    {'points': [{'covered': True, 'coord': [51.583017, -0.226472]}]}
    """

    location_config = get_location_config()
    latitude = location_config[location]["latitude"]
    longitude = location_config[location]["longitude"]
    params = {"coord": f"{latitude},{longitude}", **_get_citymapper_auth()}
    r = requests.get(
        url=f"{base_endpoint}/singlepointcoverage", params=params, timeout=1
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

    arrival = datetime.datetime.now().date()
    arrival = datetime.datetime(arrival.year, arrival.month, arrival.day)
    arrival += datetime.timedelta(hours=hour_end, minutes=30)
    arrival = str(arrival.astimezone(pytz.timezone("Europe/London")))
    try:
        travel_time = get_travel_time(start, end, arrival)
    except requests.exceptions.ReadTimeout:
        lgg.info("get_travel_time: requests.exceptions.ReadTimeout")
        travel_time = {"travel_time_minutes": None}
    return {"start": start, "end": end, "travel_time": travel_time}
