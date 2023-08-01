#!/usr/bin/python3.5

import json
import os
import sqlite3
import time
from datetime import datetime, timezone
from enum import Enum

import amiami
import requests as r

db_file = os.path.join(os.path.dirname(__file__), "fumo.db")
json_file = fn = os.path.join(os.path.dirname(__file__), "amiami.json")

AVAILABILITY_TO_PING_OVER = [
    "Available",
    "Pre-order"
]

def main():

    conn = sqlite3.connect(db_file)
    c = conn.cursor()

    make_schema(conn, c)

    print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    query = "touhou plush"
    results = amiami.search(query)

    data = load_json_file()
    discord_url = data['discord_webhook_url']

    roleIdToPing = data['roleIdToPing'] if 'roleIdToPing' in data else None

    postedItem = False
    for item in results.items:
        print(item.productName)
        postedItem = postedItem or check_item(item, conn, c, discord_url)

    if postedItem and roleIdToPing:
        msg = make_message(roleIdToPing)
        send_message(msg, discord_url)
        
    conn.close()


def make_schema(conn, c):
    schema = """
    CREATE TABLE IF NOT EXISTS "amiami" (
        "productCode" TEXT NOT NULL,
        "availability" TEXT NOT NULL,
        "price" INTEGER,
        PRIMARY KEY ("productCode")
    );
    """
    c.execute(schema)
    conn.commit()


def load_json_file():
    with open(json_file) as data_file:
        data = json.load(data_file)
        return data


def get_new_item_embed(item):
    # just hash the id and grab last 3 bytes for color
    color = hash(item.productCode) % 0xFFFFFF
    embed = {
        'title':
        '【{}】 - {}'.format(item.productCode, item.availability),
        'description':
        '{}\n'.format(item.productName),
        'url':
        '{}'.format(item.productURL),
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
    return embed


def check_item(item, conn, c, webhook_url):
    c.execute(
        "SELECT productCode, price, availability FROM amiami WHERE productCode=?",
        (item.productCode, ))
    oldItem = c.fetchone()

    if oldItem:
        if oldItem[2] != item.availability or oldItem[1] != item.price:
            # probably updated?
            print("{} updated!".format(item.productName))
            update_item(item, conn, c)
            resp = get_new_item_embed(item)
            send_embed(resp, webhook_url)
            return item.availability in AVAILABILITY_TO_PING_OVER
        # if it's an old item, we want to not execute stuff below
        return False
    # new item, let's save and send
    print("{} found!".format(item.productName))
    save_item(item, conn, c)

    resp = get_new_item_embed(item)
    send_embed(resp, webhook_url)

    return item.availability in AVAILABILITY_TO_PING_OVER


def save_item(item, conn, c):
    c.execute("INSERT INTO amiami VALUES (?, ?, ?)", (
        item.productCode,
        item.availability,
        item.price,
    ))
    conn.commit()


def update_item(item, conn, c):
    c.execute(
        "UPDATE amiami SET availability=?, price=? WHERE productCode = ?", (
            item.availability,
            item.price,
            item.productCode,
        ))
    conn.commit()

def make_message(roleIdToPing):
    return "<@&{}>, fumos have been spotted on amiami for purchase".format(roleIdToPing)

def send_message(message, webhook_url):
    payload = {'content': message, 'username': 'Fumo Pinger'}
    payload_json = json.dumps(payload)
    response = r.post(webhook_url,
                      payload_json,
                      headers={'Content-Type': 'application/json'})
    if response.status_code != 200 and response.status_code != 204:
        jsonError = json.loads(response.text)
        if('retry_after' not in jsonError):
            return
        sleepTime = (jsonError['retry_after'] / 1000) + 1
        print("Error: ", jsonError["message"])
        print("Sleeping for {}s".format(sleepTime))
        time.sleep(sleepTime)  # goodnight my prince
        send_message(message, webhook_url)  # attempt sending again


def send_embed(embed, webhook_url):
    payload = {'embeds': [embed], 'username': 'Fumo Hunter'}
    payload_json = json.dumps(payload)
    response = r.post(webhook_url,
                      payload_json,
                      headers={'Content-Type': 'application/json'})
    if response.status_code != 200 and response.status_code != 204:
        jsonError = json.loads(response.text)
        if('retry_after' not in jsonError):
            return
        sleepTime = (jsonError['retry_after'] / 1000) + 1
        print("Error: ", jsonError["message"])
        print("Sleeping for {}s".format(sleepTime))
        time.sleep(sleepTime)  # goodnight my prince
        send_embed(embed, webhook_url)  # attempt sending again


if __name__ == "__main__":
    main()
