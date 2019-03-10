#!/usr/bin/python3.5
import sys
import os
import json
import twitter
import urllib.parse
import requests
from datetime import datetime
import pprint
from hashlib import md5


def load_json_file():
    with open(json_file) as data_file:
        data = json.load(data_file)
        return data


def save_json():
    with open(json_file, "w") as outfile:
        json.dump(data, outfile, indent=2)


def send_embed(url, embed):
    payload = {'embeds': [embed]}
    payload_json = json.dumps(payload)
    response = requests.post(url, payload_json, headers={'Content-Type': 'application/json'})
    if response.status_code != 200 and response.status_code != 204:
        print("Error: ", response.text)


def get_twitter_embed(tweet, idx):
    # idx is which image has the fumo
    # pull the stamp into a datetime which has hardcoded UTC
    # twitter says it'll always be UTC, so yeah
    stamp = datetime.strptime(tweet.created_at, "%a %b %d %H:%M:%S +0000 %Y")
    m = md5()
    m.update(bytes(tweet.user.screen_name, 'utf8'))
    # and then just pull the last 3 bytes and convert to int
    color = int.from_bytes(m.digest()[-3:], "little")

    embed = {
        'description': tweet.text,
        "author": {
            "name": "{}(@{})".format(tweet.user.name, tweet.user.screen_name),
            "url": "https://twitter.com/{}".format(tweet.user.screen_name),
            "icon_url": tweet.user.profile_image_url_https,
        },
        'url': "https://twitter.com/{}/status/{}".format(tweet.user.screen_name, tweet.id_str),
        'footer': {
        },
        'color': color,
        'timestamp': stamp.isoformat(),
        'image': {
            'url': tweet.media[idx].media_url_https,
        },
    }
    if len(tweet.media) > 1:
        embed['footer']['text'] = '{} images'.format(len(tweet.media))
    if tweet.truncated:
        embed['description'] = tweet.extended_tweet.full_text
    print(json.dumps(embed, indent=4))
    return embed


def chunk_list_on_pred(fn, l):
    chunked_l = []
    for entry in l:
        # do we satisfy pred?
        if fn(entry, chunked_l, l):
            if len(chunked_l) > 0: # do we have previous entries?
                yield chunked_l # yield before making new
            chunked_l = [entry] # start a new list
        else:
            chunked_l.append(entry) # else just keep adding to current list
    yield chunked_l # this was a bug previously, dropping the last one


def acc_str_len_check(entry, chunked_l, l):
    # arbitrary, just 500 - X, where X is constant of of stuff in search query not dynamiclly made. 200 is safe guess
    max_char = 300
    # len(" OR <name>") = len(screen_name) + 4
    chunked_str_lens = map(lambda s: len(s.screen_name) + 4, chunked_l)
    return sum(chunked_str_lens) + len(entry.screen_name) > max_char


def do_search(api, discord_url):

    user_list = api.GetFriends()
    # this whole chunk this is because of how I'm doing twitter's feed check
    # I'm literally just querying everyone's feed that has an image and isn't
    # a retweet with a search. And twitter imposes some arbitrary character limit
    # so I have to play smart and can't send all the accounts at once so we
    # chunk them based on the length of the total names
    chunked_lists = chunk_list_on_pred(acc_str_len_check, user_list)

    # since we're chunking list based on length and not time, tweets may come out of order
    # so every chunked_list, we start from the highest known tweet id from last run
    # ensures we get them all
    # then the next since_id is the highest we've seen in any chunked_list
    highest_tweet_id = data['since_id_for_list']
    try:
        for mini_user_list in chunked_lists:
            # query = <tweets from users we follow> that tweet images  minus any retweets
            search_query = "%s -filter:retweets filter:twimg" \
                           % " OR ".join(list(map(lambda x: "from:%s" % x.screen_name, mini_user_list)))

            search_params = {
                "q": search_query,
                "result_type": "recent",
                "count": 20,
                "since_id": data['since_id_for_list']
            }

            query_str = urllib.parse.urlencode(search_params)
            search_res = api.GetSearch(raw_query=query_str)
            while search_res:
                for tweet in reversed(search_res):  # get oldest first to make sense when we post
                    if tweet.media:  # should always be true
                        print('checking {}:{}'.format(tweet.user.screen_name, tweet.id_str))
                        for idx, media in enumerate(tweet.media):
                            if fumo_detector.check(url) > 0:
                                full_url = media.expanded_url
                                try:
                                    api.PostRetweet(status_id=tweet.id)
                                    embed = get_twitter_embed(tweet, idx)
                                    send_embed(discord_url, embed)
                                    continue  # can only retweet thing once, so skip other media
                                except twitter.error.TwitterError as e:
                                    # retweet error, don't care. shouldn't happen but happens on 2nd run of debug
                                    # not sure why it's a list, but that's how it's given to me in the api
                                    if e.message[0]['code'] == 327:
                                        print('Already retweeted {}'.format(tweet.id))
                                        pass
                                    else:
                                        raise e

                    search_params['since_id'] = tweet.id
                    highest_tweet_id = max(tweet.id, highest_tweet_id)
                query_str = urllib.parse.urlencode(search_params)
                search_res = api.GetSearch(raw_query=query_str)
            save_json()
    except Exception as e:
        raise e
    finally:
        # just save the last tweet id in case of w/e
        data['since_id_for_list'] = highest_tweet_id
        save_json()


def main():
    print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    api = twitter.Api(consumer_key=data['cons_key'],
                      consumer_secret=data['cons_secret'],
                      access_token_key=data['access_token'],
                      access_token_secret=data['access_token_secret'])

    do_search(api, discord_url)


json_file = fn = os.path.join(os.path.dirname(__file__), "twitter.json")

data = load_json_file()  # we make this global cause life easier
discord_url = data['discord_webhook_url']

if __name__ == '__main__':
    main()
