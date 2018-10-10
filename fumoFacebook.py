#!/usr/bin/python3.5
import requests
import json
import re
from pprint import pprint
from datetime import datetime
from threading import Timer
import sys
import os
import time
import sqlite3

def send_message(message):
    global url
    payload = {'content': message}
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
    keep_going = True
    while keep_going:
        feed_data = get_feed_before(data['cursor_before'])
        for post in reversed(feed_data['data']):
            if 'object_id' not in post or has_been_posted(post['object_id']):
                continue

            insert_post(post['object_id'])

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

        # so this check was created because the cursors tend to bug out if you update them
        # too fast or something. So now we only update cursor when the thing is maxed
        if len(feed_data['data']) == int(limit):
            data['cursor_before'] = feed_data['paging']['cursors']['before']
        else:
            keep_going = False
    save_json()
    print("Saving JSON")


def get_feed_before(token):
    feed_url = json_feed_url_format % (fb_page_id, fb_access_token, token)
    print("Checking: %s" % (token))
    return requests.get(feed_url).json()

def insert_post(id):
    c.execute("INSERT INTO posts VALUES (?)", (id,))
    conn.commit()

def has_been_posted(id):
    c.execute("SELECT id FROM posts WHERE id=?", (id,))
    if c.fetchone(): # I know you could just return it but I want to turn them into bools
        return True
    return False

def create_table_if_not_exist():
    query = "CREATE TABLE  IF NOT EXISTS `posts` ( `id` TEXT UNIQUE, PRIMARY KEY(`id`) )"
    conn.execute(query)

json_file = fn = os.path.join(os.path.dirname(__file__), "facebook.json")
data = load_json_file()
fb_access_token = data['fb_access_token']
fb_page_id = "1484687218491774" #fumo page id
fields = "full_picture message story object_id".replace(' ',',')
limit = "20"
# needs to be done this way because we fill in the other stuff later while these are "hardcoded" into the url
json_feed_url_format = "https://graph.facebook.com/v2.9/%s/feed?access_token=%s&limit="+limit+"&before=%s&fields="+fields

#webhook url
url = data['discord_webhook_url'];

# db stuff
db_file = os.path.join(os.path.dirname(__file__), "fumo.db")
conn = sqlite3.connect(db_file)
c = conn.cursor()

if __name__ == '__main__':
    create_table_if_not_exist()
    check_feed()
