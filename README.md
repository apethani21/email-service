# Email service containing weather, travel and news updates: 

This is a significant update on [morning-email-update](https://github.com/apethani21/morning-email-update). Here, we:

- Get travel related tweets from Twitter using [tweepy](https://www.tweepy.org/)
- Get weather information from the [Met-Office](https://metoffice.apiconnect.ibmcloud.com/metoffice/production/)
- Scrape current events from [Wikipedia](https://en.m.wikipedia.org/wiki/Portal:Current_events)
- Get news article from [Google's news API](https://newsapi.org/s/google-news-api)

and upload to a MongoDB database regularly. The emailer now queries the database to get the latest travel tweets, weather predictions and news, creates and sends an email using smtplib and Amazon SES.
