#!/usr/bin/python3.5
import requests as r
import json
from datetime import datetime, timezone
import dateutil.parser
import sqlite3
import time
import os
from enum import Enum

class ItemStatus(Enum):
    New = 1
    Expiring = 2
    Unchanged = 3


def load_json_file():
    with open(json_file) as data_file:
        data = json.load(data_file)
        return data


def get_new_item_embed(item):
    rating = item['Seller']['Rating']
    # gen. some strings to not have it jumbled in dict
    bid_string = "bid" if int(item['Bids']) == 1 else "bids"
    initprice = item['Initprice'][:-3] if item['Initprice'].endswith(".00") else item['Initprice']
    currprice = item['Price'][:-3] if item['Price'].endswith(".00") else item['Price']
    # id is always letter followed by numbers
    # chop off letter, -> hex -> get last 6 to ensure it's only 3 bytes -> back to dec.
    hexStr = hex(int(item['AuctionID'][1:]))
    color = int(hexStr[-6:], 16)
    embed = {
        'title':'【{}】 - {}'.format(item['AuctionID'], item['Seller']['Id']),
        'description':'{}\n【[YAJ]({})】　【[Buyee]({})】\n'.format(
            item['Title'],
            item['AuctionItemUrl'],
            item['AuctionItemUrl'].replace("page.auctions.yahoo.co.jp/jp", "buyee.jp/item/yahoo")
        ),
        'url':item['AuctionItemUrl'],
        'footer':{
            'text':'+{} | -{}　　{} {}　　　　　Ends at: '.format(
            rating['TotalGoodRating'],
            rating['TotalBadRating'],
            item['Bids'], bid_string
            ),
        },
        'fields': [
            {
                'name':'Opening Price:',
                'value': "{:,}円".format(int(initprice)),
                'inline': True
            }, {
                'name':'Current Price:',
                'value': "{:,}円".format(int(currprice)),
                'inline': True,
            },
        ],
        'color':color,
        'timestamp':item['EndTime'],
        'image': {
            #'url': item['Img']['Image1'],
            'url': item['Thumbnails']['Thumbnail1'],
        },
    }

    if 'Bidorbuy' in item:
        if item['Bidorbuy'] == item['Price']:
            # overwrite
            embed['fields'] = [
                {
                    'name':'Buy it now for:',
                    'value': "{:,}円".format(int(currprice)),
                    'inline': True,
                }
            ]
        else:
            # append
            embed['fields'].append({
                'name':'Buyout Price:',
                'value': "{:,}円".format(int(item['Bidorbuy'][:-3])),
                'inline': True,
            })

    return embed

def get_expiring_item_embed(item):
    embed = get_new_item_embed(item)
    embed['title'] += " - AUCTION ENDING"
    return embed

# will return extended item info from the url in item.
def fetch_extended_item_info(item):
    url = item['ItemUrl']
    return fetch_extended_item_info_from_url(url)

def fetch_extended_item_info_from_url(url):
    buyee_data = {
        'appid': data['app_id'],
        'output': 'json',
    }
    req = r.get(url, buyee_data)
    resp_obj = parse_response(req.text)
    return resp_obj['ResultSet']['Result']

# have we posted about it before?
def check_item(item):
    c.execute("SELECT AuctionID FROM auctions WHERE AuctionID=?", (item['AuctionID'],))
    if c.fetchone():
        time_diff = dateutil.parser.parse(item['EndTime']) - datetime.now(timezone.utc)
        largest_exp_time = 60 * 20
        smallest_exp_time = 60 * 6
        if smallest_exp_time <= time_diff.total_seconds() <= largest_exp_time:
            return ItemStatus.Expiring
        return ItemStatus.Unchanged

    c.execute("INSERT INTO auctions VALUES (?)", (item['AuctionID'],))
    return ItemStatus.New


def parse_response(text):
    prefix = "loaded("
    suffix = ")"
    stripped = text[len(prefix): -1 * len(suffix)]
    return json.loads(stripped)


def check_items(items):
    for item in items:

        status = check_item(item)
        # don't care if item isn't new or about to expire
        if status is ItemStatus.Unchanged:
            continue
        # commit any changes before we error somewhere and rollback
        conn.commit()
        # get more info about item to make embed
        item = fetch_extended_item_info(item)
        if status is ItemStatus.New:
            resp = get_new_item_embed(item)
            send_embed(resp)
            # prevent discord rate limiting us
            time.sleep(1)

def send_embed(embed):
    global discord_url
    payload = {'embeds': [embed], 'username': 'Fumo Hunter'}
    payload_json = json.dumps(payload)
    response = r.post(discord_url, payload_json, headers={'Content-Type':'application/json'})
    if response.status_code != 200 and response.status_code != 204:
        print("Error: ", response.text)

def main():
    print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    buyee_data = {
        'query': 'ふもふも',
        'appid': data['app_id'],
        'output': 'json',
        'page': 1
    }
    url = 'http://auctions.yahooapis.jp/AuctionWebService/V2/search?'

    keep_reading = True
    while keep_reading:
        req = r.get(url, buyee_data)
        resp_obj = parse_response(req.text)

        check_items(resp_obj['ResultSet']['Result']['Item'])
        attr = resp_obj['ResultSet']['@attributes']
        next_id = int(attr['firstResultPosition']) - 1 + int(attr['totalResultsReturned'])
        if next_id == int(attr['totalResultsAvailable']):
            keep_reading = False
        else:
            buyee_data['page'] += 1


db_file = os.path.join(os.path.dirname(__file__), "fumo.db")
conn = sqlite3.connect(db_file)
c = conn.cursor()

json_file = fn = os.path.join(os.path.dirname(__file__), "buyee.json")
data = load_json_file() #we make this global cause life easier
discord_url = data['discord_webhook_url']
main()
conn.close()
