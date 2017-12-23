#!/usr/bin/python3.5
import requests as r
import json
from datetime import datetime, timezone
import dateutil.parser
import sqlite3
import time
import os


def load_json_file():
    with open(json_file) as data_file:
        data = json.load(data_file)
        return data


def pretty_print_seconds(time_left):
    if time_left < 60:
        text = "Seconds" if time_left > 1 else "Second"
        return "%s Seconds" % time_left
    ppt = []
    if time_left / 60 >= 1:
        minutes_left = int(time_left / 60)
        sub_minutes = minutes_left % 60
        if not sub_minutes == 0:
            text = "Minutes" if sub_minutes > 1 else "Minute"
            ppt.append("%s %s" % (sub_minutes, text))
        time_left = minutes_left - sub_minutes
    if time_left/60 >= 1:
        hours_left = int(time_left / 60)
        sub_hours = hours_left % 24
        if not sub_hours == 0:
            text = "Hours" if sub_hours > 1 else "Hour"
            ppt.append("%s %s" % (sub_hours, text))

        time_left = hours_left - sub_hours
    if time_left/24 >= int(time_left / 24):
        days_left = int(time_left / 24)
        if not days_left == 0:
            text = "Days" if days_left > 1 else "Day"
            ppt.append("%s %s" % (days_left, text))

    return ", ".join(reversed(ppt))


def get_new_item_str(item):
    time_diff = dateutil.parser.parse(item['EndTime']) - datetime.now(timezone.utc)
    output_str = "【%s】Current Bid:%s¥\nTime Left - %s\n%s" \
                 % (item['AuctionID'],
                    item['CurrentPrice'],
                    pretty_print_seconds(time_diff.total_seconds()),
                    item['AuctionItemUrl'])
    return output_str


def get_expiring_item_str(item):
    time_diff = dateutil.parser.parse(item['EndTime']) - datetime.now(timezone.utc)
    output_str = "Auction Ending!【%s】Current Bid:%s¥\nTime Left - %s\n%s" \
                 % (item['AuctionID'],
                    item['CurrentPrice'],
                    pretty_print_seconds(time_diff.total_seconds()),
                    item['AuctionItemUrl'])
    return output_str


def check_item(item):
    c.execute("SELECT AuctionID FROM auctions WHERE AuctionID=?", (item['AuctionID'],))
    if c.fetchone():
        time_diff = dateutil.parser.parse(item['EndTime']) - datetime.now(timezone.utc)
        largest_exp_time = 60 * 20
        smallest_exp_time = 60 * 6
        if smallest_exp_time <= time_diff.total_seconds() <= largest_exp_time:
            return get_expiring_item_str(item)
        return None

    c.execute("INSERT INTO auctions VALUES (?)", (item['AuctionID'],))
    return get_new_item_str(item)


def parse_response(text):
    prefix = "loaded("
    suffix = ")"
    stripped = text[len(prefix): -1 * len(suffix)]
    return json.loads(stripped)


def check_items(items):
    for item in items:
        resp = check_item(item)
        if resp:
            print(resp)
            send_message(resp)
            conn.commit()
            time.sleep(1)


def send_message(message):
    global discord_url
    payload = {'content': message, 'username': 'Fumo Hunter'}
    r.post(discord_url, payload)


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
        print(resp_obj['ResultSet']['@attributes'])
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
