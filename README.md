# Birdwatch

## Overview
Birdwatch is a Twitter bot for notable [eBird](https://ebird.org) sightings in a given area. eBird, run by the Cornell Lab of Ornithology, is the largest online birding community, with more than 100 million bird sightings logged annually around the world.

## What makes a sighing notable

From eBird:
> Notable observations can be for locally or nationally rare species or are otherwise unusual, e.g. over-wintering birds in a species which is normally only a summer visitor.

## Usage
Set Birdwatch to run at regular intervals using a job scheduler like cron. Birdwatch uses Tweepy and Twitter's v2 API to tweet. It needs Python 3.7 or higher.

## Configuration
Specify the counties you want to monitor for bird sightings with the `REGIONS`  variable in the config file. For a list of region codes in your area, call eBird's Sub Region List endpoint [like this](https://documenter.getpostman.com/view/664302/S1ENwy59#382da1c8-8bff-4926-936a-a1f8b065e7d5). eBird's hierarchy includes region codes for countries, states (subnational1) and counties (subnational2). Birdwatch can only handle counties.

You can also specify birds to ignore by adding their species codes to `IGNORE`. Species codes are included in each sighting returned by the API.

## Under the hood
Birdwatch calls eBird's endpoint for notable sightings, then does a few things to clean up the data before tweeting.

eBird's data includes both verified and unverified sightings. Verified sightings are ones that have been double-checked by one of eBird's data editors.

Birdwatch tweets only verified sightings, so its first step is to extract them from the data. After that, Birdwatch removes duplicate sightings (instances of the same bird in the same place at the same time), checks to see if a given sighting has already been tweeted and, if not, [tweets it](https://twitter.com/DFWBirds/status/1510429478824169478).

Tweets include the name of the bird, the eBird hotspot where it was seen, the county and a link to more info about the bird. A reply to each tweet includes a Google Maps link to the approximate coordinates where the bird was seen.