# Fumo Discord Bots
---

Collection of bots I've written over a while for fumo discord server
Most, if not all, of them don't follow any real standards or common practices because I wrote them as time went on instead of sitting down and doing them all at once

There's a lot of repeated code in places, because I just copied the first version and rolled with it
I left most files without a main because of scope issues and it made it 10x easier to write initally. And most of them print out 'useless' data but I have a logrotate conf to zip them up so it shouldn't take up much space. Around 2 MB for all the logs
Fumo detector comes with the models, but you probably need to install [object\_detection](https://github.com/tensorflow/models/blob/master/research/object_detection/g3doc/installation.md)
---
Bots for

* 4chan
* Buyee
* Twitter
* Facebook
* Suruguya



## 4chan
First one I wrote and kept adding on to it

* check if thread 404'd
* if it did, find new thread
* if no new thread, exit
* go through posts and look at pics to see if fumos

## Buyee
this is the only one to use the sqlite db at the moment

* query api to check for fumos
* for each page it finds, go through postings
* check db if we've seen it before and ending soon
* post if new, or ending soon

## Twitter
Bot is [here](https://twitter.com/FumoHonkBot)

* Check if anyone has mentioned bot and contains image that has fumo so can retweet
* Check if anyone has tweeted that the bot follows and contains image that has fumo so can retweet

## Facebook

* Go through fumo facebook page and link anything that has an image, pretty much


## Suruguya
* Checks suruguya for `東方 ふもふも ぬいぐるみ`  and links any different priced items to the discord channel
