#!/usr/bin/python3.5
import sys
import os
import json
import twitter
import numpy as np
import cv2
from urllib.request import urlopen
import urllib.parse
import glob
import requests
from datetime import datetime
import fumo_detector


def load_json_file():
    with open(json_file) as data_file:
        data = json.load(data_file)
        return data


def save_json():
    with open(json_file, "w") as outfile:
        json.dump(data, outfile, indent=2)


def send_message(message):
    global discord_url
    payload = {'content':message,'username':'TWITTER BOT'}
    requests.post(discord_url,payload)


def do_mentions(api):
    mentions = api.GetMentions(count=200, since_id=data['since_id'])
    if mentions:
        oldest_first = sorted(mentions, key=lambda k: k.id)
        for mention in oldest_first:
            if mention.media:
                url = mention.media[0].media_url
                print('checking %s:%s' % (mention.id, url))
                if fumo_detector.check(url) > 0: # any fumos detected?
                    print('detected fumo')
                    full_url = mention.media[0].expanded_url
                    api.PostRetweet(status_id=mention.id)
                    send_message('%s' % full_url)
                else:
                    print('no soft girls in tweet')
            data['since_id'] = mention.id
    else:
        print('no new tweets')
    save_json()

def do_search(api):

    user_list = api.GetFriends()
    # query = <tweets from users we follow> that tweet images  minus any retweets
    search_query = "%s -filter:retweets filter:twimg" \
                   % " OR ".join(list(map(lambda x: "from:%s" % x.screen_name, user_list)))

    search_params = {
        "q": search_query,
        "result_type": "recent",
        "count": 20,
        "since_id": data['since_id_for_list']
    }

    query_str = urllib.parse.urlencode(search_params)
    print(query_str)
    search_res = api.GetSearch(raw_query=query_str)
    while search_res:
        for tweet in reversed(search_res): #get oldest first to make sense when we post
            if tweet.media: #should always be true
                for media in tweet.media:

                    url = media.media_url
                    print('checking %s:%s' % (tweet.id, url))
                    if fumo_detector.check(url) > 0:
                        print('detected fumo')
                        full_url = media.expanded_url
                        api.PostRetweet(status_id=tweet.id)
                        send_message('%s' % full_url)
                    else:
                        print('no soft girls for tweet')
            # I update it every loop incase something breaks, don't repeat next time
            data['since_id_for_list'] = tweet.id
            search_params['since_id'] = data['since_id_for_list']
        query_str = urllib.parse.urlencode(search_params)
        search_res = api.GetSearch(raw_query=query_str)
    save_json()


def main():
    print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("Doing mentions since %s" % data['since_id'])

    api = twitter.Api(consumer_key=data['cons_key'],
                      consumer_secret=data['cons_secret'],
                      access_token_key=data['access_token'],
                      access_token_secret=data['access_token_secret'])

    do_mentions(api)

    do_search(api)


json_file = fn = os.path.join(os.path.dirname(__file__), "twitter.json")

data = load_json_file() #we make this global cause life easier
discord_url = data['discord_webhook_url']
main()
