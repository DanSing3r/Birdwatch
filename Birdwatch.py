import config
import keys
import requests
import json
from datetime import datetime, timedelta
import tweepy
import time
import os

def timestamp():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def get_notable(region, timeframe=config.TIMEFRAME):

    url = ('https://api.ebird.org/v2/data/obs/'
        f'{region}/recent/notable?back={timeframe}')
    headers = {'X-eBirdApiToken':keys.EBIRD_TOKEN}

    response = requests.request('GET', url, headers=headers)

    return response

def load(response, county, ignore=config.IGNORE):

    observations = json.loads(response.content)
    valids = []
    invalids = []

    for o in observations:
        if o['obsValid'] and o['speciesCode'] not in ignore:
            valids.append(dict(o, county=county))
        elif not o['obsValid']:
            invalids.append(o)

    return valids, invalids

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

def tweet(birds, interval=config.DELAY):

    client = tweepy.Client(consumer_key=keys.CONSUMER_KEY, consumer_secret=
        keys.CONSUMER_SECRET, access_token=keys.ACCESS_TOKEN,
        access_token_secret=keys.ACCESS_SECRET)

    responses = []

    for bird in birds:

        if bird['howMany'] > 1:
            group_detail = f' (group of {bird["howMany"]})'

        else:
            group_detail = ''

        name = cleanup(bird['comName']).replace(' ', '_').replace('\'', '')
        about = f'https://allaboutbirds.org/guide/{name}/'

        b_response = requests.request('GET', about)
        if not response.status_code == 200:
            about = None

        map = ('https://www.google.com/maps/search/?api=1&query=' +
            str(bird['lat']) + '%2C' + str(bird['lng']))

        if not bird['locationPrivate']:
            location = f'at {cleanup(bird["locName"])}, {bird["county"]} County'
        elif bird['locationPrivate']:
            location = f'in {bird["county"]} County'

        if about:
            tweet = (f'{bird["comName"]}{group_detail} spotted '
                f'{location} {about}')
        elif map:
            tweet = (f'{bird["comName"]}{group_detail} spotted '
                f'{location} {map}')

        try:
            t_response = client.create_tweet(text=tweet)
            responses.append(t_response)

        except Exception as e:
            responses.append((e, tweet))
            birds.remove(bird)

        if about and map:
            try:
                th_response = client.create_tweet(text=map,
                    in_reply_to_tweet_id=t_response.data['id'])
                responses.append(th_response)

            except Exception as e:
                responses.append((e, tweet))

        time.sleep(interval)

    return birds, responses

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

def cleanup(string):

    # Remove parentheticals, double hyphens
    if '(' in string:
        start = string.index('(')
        end = string.index(')')
        if end == len(string)-1:
            string = string[:start-1]

        else:
            string = (string[:start] + string[end+2:])

    # Replace double hyphen with en dash
    if '--' in string:
        string = string.replace('--', ' \u2013 ')

    # Replace with en dash
    if '~' in string:
        string = string.replace('~', ' \u2013 ')

    return string

if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.realpath(__file__))
    os.chdir(script_dir)

    tweets = []

    for region in config.REGIONS:
        response = get_notable(region[1])
        print(f'{timestamp()}: Got {region[0]} County')

        valids, invalids = load(response, region[0])
        uniques = dedupe(valids)
        tweetable = remove_tweeted(uniques)
        tweets += tweetable

        # Logging
        if invalids:
            print(f'{len(valids)} valid, {len(uniques)} unique, '
                f'{len(tweetable)} tweetable / {len(invalids)} invalid '
                f'({invalids[0]["obsDt"]}: {invalids[0]["comName"]} '
                f'[{invalids[0]["speciesCode"]}])')
        else:
            print(f'{len(valids)} valid, {len(uniques)} unique, '
                f'{len(tweetable)} tweetable / 0 invalid')

    if tweets:
        tweeted, responses = tweet(tweets)
        update_tweeted(tweeted)

        # Logging
        if responses:
            print(f'Twitter responses: {responses}')
    print()
