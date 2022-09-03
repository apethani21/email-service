import os
import bs4
import pymongo
import requests
import logging as lgg
from time import sleep
from datetime import datetime, time
from newsapi import NewsApiClient

required_sources = (
    "BBC News",
    "Bloomberg",
    "CNBC",
    "Financial Times",
    "Politico",
    "Reuters",
    "Sky News",
)

lgg.basicConfig(level=lgg.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def get_news_api_key():
    home = os.path.expanduser("~")
    with open(f"{home}/keys/google-news-api/news_api_key", "r") as f:
        news_api_key = f.read().rstrip("\n")
    return news_api_key


def get_google_news_sources():
    with open(f"./configs/google_news_sources", "r") as f:
        sources = f.read().strip()
    return sources


def get_google_news(sources, from_param=None):
    api_key = get_news_api_key()
    client = NewsApiClient(api_key)
    if from_param is None:
        from_param = datetime.combine(datetime.today(), time.min).strftime(
            "%Y-%m-%dT%H:%M:%S"
        )
    try:
        news = client.get_everything(
            sources=sources, from_param=from_param, language="en"
        )
    except requests.exceptions.ReadTimeout as e:
        lgg.warning(f"requests.exceptions.ReadTimeout - retrying after 5 minutes")
        sleep(300)
        news = client.get_everything(
            sources=sources, from_param=from_param, language="en"
        )
    now = datetime.now()
    news["_id"] = int(now.strftime("%Y%m%d%H%M"))
    return news


def get_wiki_current_events():
    now = datetime.now()
    today_date = now.strftime("%Y_%B_%-d")
    url = "https://en.m.wikipedia.org/wiki/Portal:Current_events"
    r = requests.get(url)
    soup = bs4.BeautifulSoup(r.content, "html.parser")
    anchors = soup.find_all("a")
    for anchor in anchors:
        anchor.replace_with_children()
    today_block = soup.find(id=today_date)
    if today_block is None:
        return None
    else:
        html = today_block.contents[-1].renderContents().decode()
        return {
            "_id": int(now.strftime("%Y%m%-d")),
            "date": now.strftime("%-d %b %Y"),
            "text": html,
        }


def query_wiki_current_events(ts=None):
    if ts is None:
        ts = datetime.now()
    doc_id = int(str(ts.date()).replace("-", ""))
    client = pymongo.MongoClient()
    db = client["wiki"]
    collection = db["currentEvents"]
    doc = collection.find_one({"_id": doc_id})
    return doc


def query_news_articles(**config):
    count = config["articles"]
    client = pymongo.MongoClient()
    db = client["googlenews"]
    collection = db["articles"]
    docs = collection.find(sort=[("_id", -1)])
    articles = []
    for doc in docs:
        doc_articles = doc["articles"]
        for article in doc_articles:
            articles.append(article)
            count -= 1
            if count == 0:
                return articles
