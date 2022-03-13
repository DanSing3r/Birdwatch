import config
import keys
import requests
import json
from datetime import datetime, timedelta
import telegram_send
import time
import os

def timestamp():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def get_notable(region, api_token):

    url = f'https://api.ebird.org/v2/data/obs/{region}/recent/notable?back={config.TIMEFRAME}'
    headers = {'X-eBirdApiToken':api_token}

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

def check_tweeted(observations, f):

    recents = []

    with open(f, 'r') as fh:
        tweeted = json.load(fh)

    for t in tweeted:
        for o in observations:
            if (o['speciesCode'] == t['speciesCode'] and
                o['locId'] == t['locId'] and o['obsDt'] == t['obsDt']):
                observations.remove(o)

    return observations

def update_tweeted(tweeted, f):

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

if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.realpath(__file__))
    os.chdir(script_dir)

    tweeted = []

    for region in config.REGIONS:
        response = get_notable(region, keys.TOKEN)
        print(f'{timestamp()}: Got region {region}')
        print(response.content)

        valids = find_valids(response)
        print(f'Valids: {len(valids)}\n{valids}')

        uniques = dedupe(valids)
        print(f'Uniques: {len(uniques)}\n{uniques}')

        tweetable = check_tweeted(uniques, config.F_TWEETED)
        print(f'Tweetable: {len(tweetable)}\n{tweetable}')

        alert(tweetable)
        if tweetable:
            tweeted += tweetable

    recents = update_tweeted(tweeted, config.F_TWEETED)
    print(f'Recently tweeted: {len(recents)}\n{recents}')
