import os
import ssl
import sys
import json
import pytz
import pymongo
import smtplib
import logging as lgg
from datetime import time, datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from tweepy_utils import query_tweets
from met_office_utils import query_met_office_prediction, bearing_to_cardinal
from news_utils import query_wiki_current_events, query_news_articles


lgg.basicConfig(level=lgg.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s')


def get_email_credentials():
    home = os.path.expanduser('~')
    with open(f"{home}/keys/gmail/sender_config.json", "r") as f:
        config = json.loads(f.read())
    return config


def get_aws_ses_credentials():
    home = os.path.expanduser('~')
    with open(f"{home}/keys/aws/ses-credentials.json", "r") as f:
        config = json.loads(f.read())
    return config


def news_to_html(articles):
    body = ""
    for article in articles:
        publish_time = article['publishedAt'].replace('T', ' ').replace('Z', ' ')
        source = article['source']['name']
        url = article.get('url')
        if url is None:
            headline = f"<b>{article['title']}</b><br>"
        else:
            headline = f"<a href={url}><b>{article['title']}</b></a><br>"
        article_body = f"""\
            {headline}
            <i>Source: {source}, {publish_time}</i><br><br>
        """
        
        body += article_body
    return body + "\n<hr>"


def weather_to_html(weather_info):
    html_bodies = []
    for area, weather in weather_info.items():
        area_clean = area.split('_')
        area_clean = ' '.join([word.capitalize() for word in area_clean])
        ts = weather["time"]
        time_clean = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S").strftime("%d %b %H:%M %p")

        body = f"""\
            <b>Time</b>: {time_clean} -- <b>{area_clean}</b><br>
            <b>Temperature</b>: {round(weather["screenTemperature"], 2)}\u00b0C<br>
        """

        wind_speed = round(weather["windSpeed10m"]*2.23694, 2)
        wind_dir = bearing_to_cardinal(weather["windDirectionFrom10m"])
        body += f"""
        <b>Wind Speed</b>: {wind_speed} mph from the {wind_dir}. <br>
        """

        body += f"""
        <b>Chance of precipitation</b>: {weather["probOfPrecipitation"]}% <br>
        <b>Rate of precipitation</b>: {weather["precipitationRate"]} mm/hour <br>
        <hr>
        """
        html_bodies.append(body)
    return "<br>".join(html_bodies)


def tweets_to_html(tweets):
    html_bodies = []
    for tweet in tweets:
        time = tweet["created_at"][4:-11]
        text = tweet["full_text"]
        body = f"""\
            <b> {time} </b><br>
            {text} <br>
        """
        html_bodies.append(body)
    return "<br>".join(html_bodies) + "\n<hr>"


def current_events_to_html(current_events):
    if current_events is None:
        return ''
    header = f"""
             <h2 style="font-size:20px;">
             Current Events - {current_events['date']}
             </h2> <br>
             <hr
              """
    return header + current_events["text"]


def create_email_html_body(**config):
    weather = query_met_office_prediction(**config)
    tweets = query_tweets(**config)
    current_events = query_wiki_current_events()
    news = query_news_articles(**config)

    weather_html = weather_to_html(weather)
    lgg.info("weather html body created")
    tweets_html = tweets_to_html(tweets)
    lgg.info("tweets html body created")
    current_events_html = current_events_to_html(current_events)
    lgg.info("current events html body created")
    news_html = news_to_html(news)
    lgg.info("news html body created")

    html = f"""
        <html>
          <body>
            <p style="color:black;">
              <h2 style="font-size:20px;">Weather</h2> <br>
              {weather_html} <br>
              <h2 style="font-size:20px;">Travel</h2> <br>
              {tweets_html} <br>
              {current_events_html} <br>
              <h2 style="font-size:20px;">Latest Headlines</h2> <br>
              {news_html} <br>
            </p>
          </body>
        </html>
    """
    return html


def send_email(html, use_ses=True):
    email_credentials = get_email_credentials()
    receiver_email = email_credentials["receiver_email"]
    sender_email = email_credentials["sender_email"]
    message = MIMEMultipart("alternative")
    message["Subject"] = f"UPDATE - {datetime.now().strftime('%a %d %b %y')}"
    html_main = MIMEText(html, "html")
    message["From"] = sender_email
    message["To"] = receiver_email
    message.attach(html_main)
    password = email_credentials["sender_password"]
    context = ssl.create_default_context()
    if use_ses:
        aws_ses_credentials = get_aws_ses_credentials()
        smtp_username = aws_ses_credentials["smtp-username"]
        smtp_password = aws_ses_credentials["smtp-password"]
        with smtplib.SMTP("email-smtp.eu-west-2.amazonaws.com",
                          port=587) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            lgg.info("sending message")
            server.send_message(message, sender_email, receiver_email)
            lgg.info("message sent")
            return

    else:
        with smtplib.SMTP_SSL("smtp.gmail.com",
                              port=587,
                              context=context) as server:
            server.login(sender_email, password)
            lgg.info("sending message")
            server.send_message(message, sender_email, receiver_email)
            lgg.info("message sent")
            return


if __name__ == "__main__":
    args = sys.argv[1:]
    args = dict([arg.split('=') for arg in args])
    config_name = args['config']
    lgg.info(f"config: {config_name}")
    with open(f'./configs/{config_name}', 'r') as f:
        config = json.loads(f.read())
    html = create_email_html_body(**config)
    send_email(html)
