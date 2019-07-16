#!/usr/bin/python3.5
import json
import os
import sqlite3
import time
from datetime import datetime, timezone
from enum import Enum

import dateutil.parser
import requests as r
import suruguya


def load_json_file():
    with open(json_file) as data_file:
        data = json.load(data_file)
        return data


def get_new_item_embed(item):
    # id is always letter followed by numbers
    # chop off letter, -> hex -> get last 6 to ensure it's only 3 bytes -> back to dec.
    hexStr = hex(int(item.productCode))
    color = int(hexStr[-6:], 16)
    embed = {
        'title':
        '【{}】'.format(item.productCode),
        'description':
        '{}\n'.format(item.productName),
        'url':
        '{}{}'.format('https://www.suruga-ya.jp/', item.productURL),
        'footer': {
            'text': '{}'.format(item.availability),
        },
        'fields': [
            {
                'name': 'Price:',
                'value': "{:,}円".format(int(item.price)),
                'inline': False
            },
        ],
        'color':
        color,
        'image': {
            'url': item.imageURL,
        },
    }
    print(embed)

    return embed


def check_item(item):
    c.execute(
        "SELECT productCode, price FROM suruguya WHERE productCode=? AND price=?",
        (
            item.productCode,
            item.price,
        ))
    if c.fetchone():
        return  # don't care if item has been seen before

    c.execute("INSERT INTO suruguya VALUES (?, ?)", (
        item.productCode,
        item.price,
    ))
    conn.commit()

    resp = get_new_item_embed(item)
    send_embed(resp)
    # prevent discord rate limiting us
    time.sleep(1)


def send_embed(embed):
    global discord_url
    payload = {'embeds': [embed], 'username': 'Fumo Hunter'}
    payload_json = json.dumps(payload)
    response = r.post(discord_url,
                      payload_json,
                      headers={'Content-Type': 'application/json'})
    if response.status_code != 200 and response.status_code != 204:
        print("Error: ", response.text)
        jsonError = json.loads(response.text)
        sleepTime = jsonError['retry_after'] / 1000
        print("Sleeping for {}s".format(sleepTime))
        time.sleep(sleepTime)


def main():
    print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    query = '東方 ふもふも ぬいぐるみ'

    for item in suruguya.search(query):
        check_item(item)


db_file = os.path.join(os.path.dirname(__file__), "fumo.db")
conn = sqlite3.connect(db_file)
c = conn.cursor()

schema = """
CREATE TABLE IF NOT EXISTS "suruguya" (
    "productCode" TEXT NOT NULL,
    "price" INTEGER,
    PRIMARY KEY ("productCode", "price")
);
"""
c.execute(schema)
conn.commit()

json_file = fn = os.path.join(os.path.dirname(__file__), "suruguya.json")
data = load_json_file()  # we make this global cause life easier
discord_url = data['discord_webhook_url']
main()
conn.close()
