import sys
import logging as lgg
from datetime import datetime, timedelta

from pymongo import MongoClient
from tweepy_utils import TweetGetter
from met_office_utils import get_met_office_weather, get_location_config
from news_utils import (get_google_news_sources,
                        get_google_news,
                        get_wiki_current_events)

lgg.basicConfig(level=lgg.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s')


def get_tweets(**kwargs):
    tweet_getter = TweetGetter()
    result_set = tweet_getter.api.user_timeline(**kwargs)
    tweets = [tweet_getter.clean_status_object(status)
              for status in result_set]
    return tweets


def get_weather(area=None):
    location = get_location_config(area)
    weather = get_met_office_weather(**location)
    return weather


def upload(source, **kwargs):

    client = MongoClient()

    if source == 'twitter':
        db = client["twitter"]
        collection = db[kwargs["screen_name"]]
        max_id_doc = collection.find_one(sort=[("_id", -1)])
        if max_id_doc is None:  # no documents
            max_id = 0
        else:
            max_id = max_id_doc["_id"]

        lgg.info(f"Aggregating from {source}")
        kwargs["since_id"] = max_id
        tweets = get_tweets(**kwargs)
        lgg.info(f"{len(tweets)} tweets retrieved")

        if not tweets:
            return
        else:
            result = collection.insert_many(tweets[::-1])
            lgg.info(f"Succesfully inserted {result.inserted_ids} into {collection.name}")
        return

    elif source == 'met-office':
        db = client["metoffice"]
        collection = db["hourly"]
        lgg.info(f"Aggregating from {source}")
        weather = get_weather(**kwargs)
        weather["_area"] = kwargs["area"]
        result = collection.insert_one(weather)
        lgg.info(f"Succesfully inserted {result.inserted_id} into {collection.name}")
        return

    elif source == 'wiki':
        db = client["wiki"]
        collection = db["currentEvents"]
        max_id_doc = collection.find_one(sort=[("_id", -1)])
        if max_id_doc is None:  # no documents
            max_id = 0
        else:
            max_id = max_id_doc["_id"]
        lgg.info(f"Aggregating from {source}")
        current_events = get_wiki_current_events()
        collection.replace_one(filter={'_id': current_events['_id']},
                               replacement=current_events,
                               upsert=True)
        lgg.info(f"Document {current_events['_id']} updated")
        return

    elif source == 'google-news':
        db = client["googlenews"]
        collection = db["articles"]
        sources = get_google_news_sources()
        lgg.info(f"Aggregating from {source}")
        latest_articles = collection.find_one(sort=[("_id", -1)])
        if latest_articles is not None:
            latest_timestamp = max([article['publishedAt'] for article in latest_articles["articles"]])
            latest_timestamp = latest_timestamp.rstrip('Z')
            from_param = datetime.strptime(latest_timestamp, "%Y-%m-%dT%H:%M:%S")
            from_param = str(from_param + timedelta(seconds=1))
            from_param = from_param.replace(' ', 'T')
            kwargs["from_param"] = from_param
            lgg.info(f"set from_param to {kwargs['from_param']}")
        news = get_google_news(sources=sources, **kwargs)
        if news["status"] != "ok":
            lgg.info(f"Status={news['status']}, code={news['code']}, message: {news['message']}")
            return
        if not news["articles"]:
            lgg.info("No new articles")
        news.pop("status")
        news.pop("totalResults")
        result = collection.insert_one(news)
        lgg.info(f"Succesfully inserted {result.inserted_id} into collection {collection.name}")
        return

    else:
        raise ValueError(f"Data source {source} not recognised.")


if __name__ == "__main__":
    """
    Common CL args to pass:
    source=twitter screen_name=northernline count=5 tweet_mode=extended
    source=met-office area=goodge_street
    source=wiki
    source=google-news
    """
    kwargs = sys.argv[1:]
    kwargs = dict([arg.split('=') for arg in kwargs])
    upload(**kwargs)
