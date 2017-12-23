#!/usr/bin/python3.5
import requests
import json
import re
import feedparser
from pprint import pprint
from datetime import datetime
from threading import Timer
import sys
import os
import time

def send_message(message):
    global url
    payload = {'content': message,'username': 'Fumo Facebook'}
    requests.post(url,payload)


def load_json_file():
    with open(json_file) as data_file:
        data = json.load(data_file)
        return data


def save_json():
    with open(json_file, "w") as outfile:
        json.dump(data, outfile, indent=2)


def check_feed():
    print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    global data
    #don't repost things in the past hour
    #was planning on throwing this in a quick db, but wasn't worth the effort
    seen_ids = set()
    feed_data = get_feed_before(data['cursor_before'])
    while feed_data['data']:
        for post in reversed(feed_data['data']):
            if 'object_id' not in post or post['object_id'] in seen_ids:
                continue

            seen_ids.add(post['object_id'])


            print_str_arr = []
            #get message if exists, else, get story, else get none
            #need ugly thing because the ``` get excluded completely if blank
            print_str_arr.append( "```%s```" %(post.get('message',post.get('story',''))) if post.get('message',post.get('story',None))\
                is not None else None)
            print_str_arr.append(post.get('full_picture',None))

            send_message('\n'.join([st for st in print_str_arr if st is not None]))

            print(post['id'])
            time.sleep(1)#delay to prevent spamming links?
            #discord ended up eating a bunch of posts even though they were logged
            #half second seems to be fine for the rate limiting, but going with 1
        data['cursor_before'] = feed_data['paging']['cursors']['before']
        feed_data = get_feed_before(data['cursor_before'])
    save_json()
    print("Saving JSON")


def get_feed_before(token):
    feed_url = json_feed_url_format % (fb_page_id, fb_access_token, token)
    print("Checking: %s" % (token))
    return requests.get(feed_url).json()

json_file = fn = os.path.join(os.path.dirname(__file__), "facebook.json")
data = load_json_file()
fb_access_token = data['fb_access_token']
fb_page_id = "1484687218491774" #fumo page id
fields = "full_picture message story object_id".replace(' ',',')
json_feed_url_format = "https://graph.facebook.com/v2.9/%s/feed?access_token=%s&limit=25&before=%s&fields="+fields

#webhook url
url = data['discord_webhook_url'];

check_feed()
