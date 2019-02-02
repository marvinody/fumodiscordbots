#!/usr/bin/python3.5
import requests
import gc
import json
import re
import feedparser
from pprint import pprint
from datetime import datetime
from threading import Timer
import sys
import os
from bs4 import BeautifulSoup
import html
import time
import numpy as np
import cv2
from urllib.request import urlopen
import fumo_detector


def update_thread():
    # bad habit but this way I don't have to pass in everywhere
    global data
    postno = data['thread']
    url = json_url_format.format(board='jp', postno=postno)
    thread_json = requests.get(url).json()
    files = []
    for post in thread_json['posts']:
        if(post['no'] > data['pno']):
            # new post detected
            print("New Post Detected %i" % post['no'])
            text = handle_post_text(post)
            send_message(text)
            data['pno'] = post['no']
            if('ext' in post and post['ext'] in ('.jpg', '.png', '.gif')):
                name, url = get_name_and_url_from_post(post)
                files.append({
                    name: name,
                    url: url
                })

            time.sleep(1)  # delay to prevent spamming links?
            # discord ended up eating a bunch of posts even though they were logged
            # half second seems to be fine for the rate limiting
            save_json()
    if 'sp_gid' in data:
        sadpanda_add(files, data['sp_gid'])


def get_name_and_url_from_post(post):
    return (
        "{filename}{ext}".format(
            filename=html.unescape(post['filename']),
            ext=post['ext']
        ),
        "https://i.4cdn.org/{board}/{time}{ext}".format(
            board='jp',
            time=post['tim'],
            ext=post['ext']
        )
    )


def handle_post_text(post):
    header = '【%s】%s' % (post['no'], post['now'])
    body = ""
    if 'com' in post:
        com = html.unescape(fix_html_tags(post['com']))
        body = '```%s```' % com
    if 'filename' in post:
        name, url = get_name_and_url_from_post(post)
        body = "{body} \n `{name}` {url} ".format(
            body=body,
            name=name,
            url=url
        )

        try:  # crashes when gif and I suspect webm too
            # add check later to prevent that
            detect_fumo_and_send_message(url)
        except Exception as inst:
            print(type(inst))
            print(inst)
    return "{}{}".format(header, body)


def fix_html_tags(com):
    soup = BeautifulSoup(com, 'html5lib')
    for m in soup.find_all('a'):
        m.replaceWithChildren()
    for br in soup.find_all('br'):
        br.replace_with('\n')
    return soup.get_text()


def send_message(message):
    global url
    payload = {'content': message, 'username': 'FUMO BOT'}
    requests.post(url, payload)


def detect_fumo_and_send_message(link):
    if fumo_detector.check(link) > 0:
        global fumo_detector_url
        print("detected fumo in 4chan post")
        payload = {'content': link}
        requests.post(fumo_detector_url, payload)


def load_json_file():
    with open(json_file) as data_file:
        data = json.load(data_file)
        return data


def save_json():
    with open(json_file, "w") as outfile:
        json.dump(data, outfile, indent=2)


def load_new_thread():
    global data
    attempt = find_new_thread()
    mention_str = ''
    if attempt is not None:
        data['thread'] = attempt
        data['sp_gid'] = sadpanda_create("Fumo - #"+str(attempt))
        data['pno'] = attempt-1  # make sure to print out THIS post, so sub 1
        send_message(mention_str + ' new thread loaded')
        return True
    else:
        # did not find, find later
        return False


def check_new_data():
    print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    global data

    if 'thread' not in data:
        if not load_new_thread():
            return
    else:
        postno = data['thread']
        url = json_url_format.format(board='jp', postno=postno)
        r = requests.get(url)
        if (
            r.status_code == 404
            or
            (
                'archived' in r.json()['posts'][0]
                and
                r.json()['posts'][0]['archived'] == 1
            )
          ):

            if not load_new_thread():
                return

    update_thread()
    save_json()
    print("Saving JSON")


def find_new_thread():
    url = catalog_url_format.format(board='jp')
    r = requests.get(url)
    json_r = r.json()

    # So this was my stupid idea to fix finding false threads
    # It won't stop from picking a random thread if 2 pop up at same time
    # but it will stop picking a thread that only mentions the word fumo once
    # hence the -5 on fate
    points_needed = 40

    poss_fields = {
        'semantic_url': [
            {'string': 'fumo', 'points': points_needed}
        ],
        'sub': [
            {'string': 'fumo', 'points': points_needed}
        ],
        'com': [
            {'string': 'fumo', 'points': points_needed / 5},
            {'string': 'plush', 'points': points_needed / 5},
            {'string': 'fate', 'points': -points_needed / 5}
        ]
    }

    poss_fields_for_string = ['semantic_url', 'sub', 'com']
    search_string = 'fumo'
    poss_new_threads = []
    for chunk in json_r:  # the catalog is chunked into pages
        page = chunk['page']  # with a page num
        threads = chunk['threads']  # and a list of threads
        for idx, thread in enumerate(threads):  # for each thread,
            thread_points = 0  # we want to calc some points, so we look at
            for field, entries in poss_fields.items():  # some specific fields
                if field in thread:  # if we have them, of course
                    for entry in entries:  # check each keyword for that field
                        occurences = thread[field].count(entry['string'])
                        points = occurences * entry['points']
                        thread_points += points  # tally them up
            # we only care about result if we are above some arbitrary threshold
            if thread_points >= points_needed:
                poss_new_threads.append(thread)

    if not poss_new_threads:
        return None

    by_date = sorted(poss_new_threads, key=lambda k: k['time'])
    most_recent = by_date[-1]
    return most_recent['no']


# logins to sadpanda and gets cookies to maintain a session
def sadpanda_login():
    # cause login doesn't return cookies cause fmlamirite
    cookies = sp.get(sadpanda_base_url).cookies
    r = sp.post(
        sadpanda_api_url,
        data={
            "UserName": sadpanda_user,
            "PassWord": sadpanda_pass,
            "method": "login"
         }
     )
    return cookies

# creates a sadpanda gallery
def sadpanda_create(title):
    if not data['upload_to_sadpanda']:
        return
    if 'PHPSESSID' not in sp.cookies:
        sadpanda_login()
    req = sp.post(
        sadpanda_api_url,
        cookies=sp.cookies,
        data={
            "method": "creategallery",
            "gname": title,
            "tos": 1,
            "comment": "Autogenerated thread submission"
        }
    )
    print(req.text)
    return req.json()['gid']


def chunks(l, n):
    n = max(1, n)
    return (l[i:i+n] for i in range(0, len(l), n))


def sadpanda_add(url_list, gid):
    if not url_list:
        return
    if not data['upload_to_sadpanda']:
        return
    if 'PHPSESSID' not in sp.cookies:
        sadpanda_login()

    chunked_list = chunks(url_list, 14)

    for sub_list in chunked_list:
        files = {}
        gc.collect()  # delete old files not used anymore. useless first loop
        idx = 1
        for entry in sub_list:
            # filename filled with 0's
            files["file"+str(idx).zfill(2)] = (
                entry['name'],
                requests.get(entry['url']).content
            )
            idx = idx + 1

        req = sp.post(
                sadpanda_add_url % gid,
                cookies=sp.cookies,
                files=files
            )


json_file = os.path.join(os.path.dirname(__file__), "thread.json")
data = load_json_file()

# set stuff for later
sp = requests.Session()
sadpanda_base_url = "https://sadpanda.moe/alice/"
sadpanda_api_url = sadpanda_base_url + "api.php"
sadpanda_add_url = sadpanda_base_url + "manage?act=add&gid=%s"
sadpanda_user = data['sadpanda_user']
sadpanda_pass = data['sadpanda_pass']


json_url_format = "https://a.4cdn.org/{board}/thread/{postno}.json"
catalog_url_format = "https://a.4cdn.org/{board}/catalog.json"
url = data['discord_webhook_url']
fumo_detector_url = data['discord_webhook_url_fumo']
if __name__ == '__main__':
    check_new_data()
