import os
import pymongo
from tweepy import API, OAuthHandler


class TweetGetter(API, OAuthHandler):

    @staticmethod
    def _get_tweepy_auth():
        home = os.path.expanduser('~')
        with open(f"{home}/keys/twitter/twitter_key", 'r') as f:
            twitter_key = f.read().rstrip('\n')
        with open(f"{home}/keys/twitter/twitter_secret_key", 'r') as f:
            twitter_secret_key = f.read().rstrip('\n')
        with open(f"{home}/keys/twitter/twitter_access_token", 'r') as f:
            twitter_access_token = f.read().rstrip('\n')
        with open(f"{home}/keys/twitter/twitter_secret_access_token", 'r') as f:
            twitter_secret_access_token = f.read().rstrip('\n')
        return {
             "twitter_key": twitter_key,
             "twitter_secret_key": twitter_secret_key,
             "twitter_access_token": twitter_access_token,
             "twitter_secret_access_token": twitter_secret_access_token
        }

    @staticmethod
    def set_tweepy_account(credentials):
        auth = OAuthHandler(credentials["twitter_key"],
                            credentials["twitter_secret_key"])
        auth.set_access_token(credentials["twitter_access_token"],
                              credentials["twitter_secret_access_token"])
        return auth

    def __init__(self):
        self._credentials = TweetGetter._get_tweepy_auth()
        self._auth = TweetGetter.set_tweepy_account(self._credentials)
        self.api = API(self._auth)

    @staticmethod
    def clean_status_object(status):
        status_json = status._json
        status_json["_id"] = status_json.pop("id")
        for key in "id_str truncated display_text_range user".split():
            try:
                status_json.pop(key)
            except KeyError:
                continue
        return status_json


def query_tweets(**config):
    client = pymongo.MongoClient()
    screen_name = config["twitter"]["screen_name"]
    count = config["twitter"]["tweet_count"]
    db = client["twitter"]
    collection = db[screen_name]
    tweets = (collection
              .find(sort=[("_id", -1)], projection={"created_at": 1, "full_text": 1})
              .limit(count))
    return list(tweets)