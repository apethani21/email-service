import os
import json
import pytz
import pymongo
import requests
import logging as lgg
from datetime import time, datetime

lgg.basicConfig(level=lgg.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s')

def get_met_office_credentials():
    home = os.path.expanduser('~')
    with open(f"{home}/keys/met-office/auth.json", "r") as f:
        credentials = json.load(f)
    return credentials


def get_location_config(area=None):
    with open(f'./configs/location.json', 'r') as f:
        location = json.loads(f.read())
    if area is None:
        return location
    else:
        return location[area]


def get_met_office_weather(latitude, longitude):
    credentials = get_met_office_credentials()
    url = "https://api-metoffice.apiconnect.ibmcloud.com/metoffice/production/v0/forecasts/point/hourly"

    headers = {"accept": "application/json", **credentials}
    headers["x-ibm-client-id"] = headers.pop("client-id")
    headers["x-ibm-client-secret"] = headers.pop("client-secret")

    params = {
        "excludeParameterMetadata": False,
        "includeLocationName": True,
        "latitude": latitude,
        "longitude": longitude
    }

    r = requests.get(url,
                     headers=headers,
                     params=params,
                     timeout=1)
    r.raise_for_status()
    return r.json()

def utc_to_gmt(ts):
    ts = datetime.strptime(ts, "%Y-%m-%dT%H:%MZ")
    utc = pytz.timezone('UTC')
    ts = utc.localize(ts).astimezone(pytz.timezone('Europe/London'))
    return ts.strftime('%Y-%m-%d %H:%M:%S')

def get_weather_timestamp(hour):
    date = datetime.combine(datetime.today(), time(hour))
    bst = pytz.timezone('Europe/London')
    date = bst.localize(date).astimezone(pytz.utc)
    return date.strftime('%Y-%m-%dT%H:%MZ')

def bearing_to_cardinal(bearing):
    if bearing is None:
        return None
    if not 0 <= bearing <= 360:
        return "Invalid bearing value"
    cardinal_directions = ["North", "North East", "East", "South East",
                           "South", "South West", "West", "North West"]
    decision_points = [180/len(cardinal_directions) + 45*i
                       for i in range(len(cardinal_directions))]
    for i, boundary in enumerate(decision_points):
        if boundary > bearing:
            return cardinal_directions[i]
    return 'North'

def query_met_office_prediction(**kwargs):
    """Argument is main config"""
    predictions = {}
    client = pymongo.MongoClient()
    db = client["metoffice"]
    collection = db["hourly"]
    weather_config = kwargs["weather"]
    for cfg in weather_config:
        area, hour = tuple(cfg.items())[0]
        timestamp = get_weather_timestamp(hour)
        lgg.info(f"searching for area={area}, timestamp={timestamp}")
        latest_predictions = collection.find_one(filter={"_area": area},
                                                 sort=[("_id", -1)])
        time_series = latest_predictions["features"][0]["properties"]["timeSeries"]
        required_prediction = None
        for datapoint in time_series:
            if datapoint["time"] == timestamp:
                predictions[area] = datapoint
                predictions[area]["time"] = utc_to_gmt(predictions[area]["time"])
                lgg.info(f"weather for area={area}, timestamp={timestamp} found")
    return predictions
