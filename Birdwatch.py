#!/usr/bin/env python3.9

import config
import keys
import requests
import json
from datetime import datetime, timedelta
import telegram_send
import tweepy
import time
import os

def timestamp():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def get_notable(region, timeframe=config.TIMEFRAME):

    url = f'https://api.ebird.org/v2/data/obs/{region}/recent/notable?back={timeframe}'
    headers = {'X-eBirdApiToken':keys.EBIRD_TOKEN}

    response = requests.request("GET", url, headers=headers)

    return response

def alert(birds):

    private = None
    messages = []

    for bird in birds:
        if bird['locationPrivate']:
            private = 'private'
        else:
            private = 'public'

        messages.append(f'{bird["obsDt"]}: {bird["comName"]} at {bird["locName"]} ({private})')

    telegram_send.send(messages=messages)

    return

def tweet(birds, interval=config.DELAY):

    client = tweepy.Client(consumer_key=keys.CONSUMER_KEY, consumer_secret=
        keys.CONSUMER_SECRET, access_token=keys.ACCESS_TOKEN,
        access_token_secret=keys.ACCESS_SECRET)

    responses = []

    for bird in birds:

        if bird['howMany'] > 1:
            group_detail = f'(group of {bird["howMany"]})'

        else:
            group_detail = ''

        if bird['locationPrivate']:
            # Add county logic
            tweet = f'{bird["comName"]} {group_detail}'
        elif not bird['locationPrivate']:
            map = f'https://www.google.com/maps/search/?api=1&query={bird["lat"]}%2C{bird["lng"]}'
            tweet = f'{bird["comName"]} {group_detail} spotted at {bird["locName"]} {map}'

        try:
            response = client.create_tweet(text=tweet)
            responses.append(response)

        except Exception as e:
            responses.append((e, tweet))
            birds.remove(bird)

        time.sleep(interval)

    return birds, responses

def find_valids(response):

    observations = json.loads(response.content)
    valids = []

    for o in observations:
        if o['obsValid']:
            valids.append(o)

    return valids

def dedupe(observations):

    uniques = []

    for o in observations:
        species = o['comName']
        if not species in (u['comName'] for u in uniques):
            uniques.append(o)

    return uniques

def remove_tweeted(observations, f=config.F_TWEETED):

    recents = []

    with open(f, 'r') as fh:
        tweeted = json.load(fh)

    for t in tweeted:
        for o in observations:
            if (o['speciesCode'] == t['speciesCode'] and
                o['locId'] == t['locId'] and o['obsDt'] == t['obsDt']):
                observations.remove(o)

    return observations

def update_tweeted(tweeted, f=config.F_TWEETED):

    with open(f, 'r') as fh:
        old = json.load(fh)

        for o in old:
            if (datetime.strptime(o['obsDt'], '%Y-%m-%d %H:%M') <
                datetime.now() - timedelta(days=config.TIMEFRAME)):
                old.remove(o)

    new = old + tweeted

    with open(f, 'w') as fh:
        json.dump(new, fh)

    return new

def get_image(bird):
    pass

def cleanup(loc_name):
    pass


if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.realpath(__file__))
    os.chdir(script_dir)

    tweets = []

    for region in config.REGIONS:
        response = get_notable(region)
        print(f'{timestamp()}: Got region {region}')
        print(response.content)

        valids = find_valids(response)
        print(f'Valids: {len(valids)}\n{valids}')

        uniques = dedupe(valids)
        print(f'Uniques: {len(uniques)}\n{uniques}')

        tweetable = remove_tweeted(uniques)
        print(f'Tweetable: {len(tweetable)}\n{tweetable}')

        alert(tweetable)
        tweets += tweetable

    if tweets:
        print(tweets)

        tweeted, responses = tweet(tweets)
        print(responses)

        update_tweeted(tweeted)
