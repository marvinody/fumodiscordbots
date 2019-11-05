#!/usr/bin/python3.5
import json
import os
import pprint
import sqlite3
import time
from datetime import datetime, timezone
from enum import Enum
from hashlib import md5

import dateutil.parser
import requests

json_file = fn = os.path.join(os.path.dirname(__file__), "instagram.json")
pp = pprint.PrettyPrinter(indent=2)


def load_json_file():
    with open(json_file) as data_file:
        data = json.load(data_file)
        return data

def save_json(data):
    with open(json_file, "w") as outfile:
        json.dump(data, outfile, indent=2)

def make_embed(user, image):
    m = md5()
    m.update(bytes(user['username'], 'utf8'))
    # and then just pull the last 3 bytes and convert to int
    color = int.from_bytes(m.digest()[-3:], "little")

    embed = {
        'description': image['text'],
        'title': 'Link',
        "author": {
            "name": user['username'],
            "url": "https://www.instagram.com/{}".format(user['username']),
            "icon_url": user['profile_pic'],
        },
        'url': "https://www.instagram.com/p/{}".format(image['shortcode']),
        'color': color,
        'timestamp': image['timestamp'],
        'image': {
            'url': image['thumbnail_url'],
        },
    }
    return embed

def send_embed(discord_url, embed):
    payload = {'embeds': [embed], 'username': 'Fumo Gram'}
    payload_json = json.dumps(payload)
    response = requests.post(discord_url,
                      payload_json,
                      headers={'Content-Type': 'application/json'})
    if response.status_code != 200 and response.status_code != 204:
        print("Error: ", response.text)
        jsonError = json.loads(response.text)
        sleepTime = jsonError['retry_after'] / 1000
        print("Sleeping for {}s".format(sleepTime))
        time.sleep(sleepTime)  # goodnight my prince
        send_embed(embed)  # attempt sending again

def update_users(data):
    for userEntry in data['users']:
        try:
            user = fetch_user(userEntry['username'])
            for image in reversed(user['images']):
                # if the image is newer, then we can post it!
                if userEntry['most_recent_id'] < image['id']:
                    embed = make_embed(user, image)
                    send_embed(data['discord_webhook_url'], embed)
                    # make sure to update this
                    userEntry['most_recent_id'] = image['id']
            pp.pprint(user)
        except Exception as e:
            print(e)
        finally:
            save_json(data)

def fetch_user(username):
    url = 'https://www.instagram.com/{}/?__a=1'.format(username)
    user = requests.get(url).json()
    return userReducer(user)

def userReducer(userData):
  user = userData['graphql']['user']
  return {
    "username": user['username'],
    "profile_pic": user['profile_pic_url'],
    "images": [imageReducer(imageData) for imageData in user['edge_owner_to_timeline_media']['edges']]
  }

def imageReducer(imageData):
    img = imageData['node']
    return {
      "text": img['edge_media_to_caption']['edges'][0]['node']['text'] if img['edge_media_to_caption']['edges'] else "",
      "image_url": img['display_url'],
      "thumbnail_url":img['thumbnail_src'],
      "is_video": img['is_video'],
      "id": img['id'],
      "shortcode": img['shortcode'],
      "timestamp":datetime.fromtimestamp(img['taken_at_timestamp']).isoformat()
    }

def main():
    data = load_json_file()  # we make this global cause life easier
    # will mutate the data and file
    update_users(data)
    # save it one more time
    save_json(data)


if __name__ == "__main__":
    main()
