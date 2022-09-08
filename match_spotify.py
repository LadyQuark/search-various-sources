import os
import argparse
import pprint
import string
import re
import random
import spotipy
from common import create_json_file, load_existing_json_file, valid_source_destination
from dotenv import load_dotenv, find_dotenv
from progress import progress
from spotipy.oauth2 import SpotifyClientCredentials
from sys import exit

# Get API keys from .env
load_dotenv(find_dotenv())
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
# Initialize Spotify and variables
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID,
                                                           client_secret=SPOTIFY_CLIENT_SECRET))
pp = pprint.PrettyPrinter(depth=6)
# Compile regex patterns
RE_EP = re.compile("^\#?\d+|(?:ep|episode|EP|episode)\s?\#?\d+")     
RE_NO_KEYWORDS = re.compile("\s+\|\s+")                                                  

def main():
    # Parse and check arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("source", help="Path of the source JSON file")
    parser.add_argument("destination", help="Path of the updated JSON file")
    parser.add_argument("-limit", help="Update only first 10 items", type=int, default=0)
    parser.add_argument("-v", "--verbose", help="Print results as they come", action="store_true")
    args = parser.parse_args()
    if not valid_source_destination(args.source, args.destination, file_ext=".json"):
        exit(1)

    print("Let's go!")

    # Get source JSON and initialize variables
    podcast_episodes = load_existing_json_file(None, None, args.source)
    total = len(podcast_episodes)
    if args.limit > 0 and args.limit <= total:
        # podcast_episodes = podcast_episodes[:args.limit]
        podcast_episodes = random.choices(podcast_episodes, k=3)
        total = args.limit
    count_untouched = 0
    count_updated = 0
    # update_results = []
    failed = []
    
    # Check each item
    for i, item in enumerate(podcast_episodes):
        if not args.verbose:
            progress(i+1, total)

        title = item['title']
        podcast = item['metadata']['podcast_title']

        # Check if field already exists
        if links := item['metadata'].get('additional_links'):
            # links.setdefault('itunes_url', item['metadata']['url'])
            if links.get('spotify_url') and links['spotify_url'] != "":
                # updated_results.append(item)
                count_untouched += 1
                print("No need to update")
                continue


        matched = False
        
        if args.verbose:
            action_str = f"Searching for: {title} | {podcast}"
            print("\n", action_str)
            print("-" * len(action_str))
        
        # Get full info of episodes with matching titles
        matching_ids = matching_episode_ids(title, podcast, args.verbose)
        matching_episodes = get_episodes(matching_ids) if len(matching_ids) > 0 else []
        
        # For each matching episode, check podcast name
        for episode in matching_episodes:
            url = episode['external_urls']['spotify']
            title_spotify = episode['name']
            podcast_spotify = episode['show']['name']
            publisher = episode['show']['publisher']

            if args.verbose:
                print(title_spotify, " | ", podcast_spotify)

            # If podcast name matches, update item and stop checking for this item
            if match_podcast(podcast, podcast_spotify, publisher):
                if args.verbose:
                    print("Found it!")
                
                matched = True
                links = item['metadata'].setdefault('additional_links', {})
                # links.setdefault('itunes_url', item['metadata']['url'])
                links.setdefault('spotify_url', url)
                item['original'].append(episode)
                count_updated += 1
                # updated_results.append(item)
                break
        
        if not matched:
            # item['metadata'].setdefault(
            #         'additional_links', {'itunes_url': item['metadata']['url']})
            failed.append(item)
            
            if args.verbose:
                print("No matches found!")


    # Create JSON files
    folder = os.path.dirname(args.destination) if args.destination.endswith(".json") else args.destination
    file_name = os.path.basename(args.destination) if args.destination.endswith(".json") else "updated_podcasts"
    create_json_file(folder, file_name, podcast_episodes)
    print(f"\n\nSpotify links for {count_updated + count_untouched} out of {total}")
    if count_updated > 0:
        create_json_file(folder, file_name, podcast_episodes)
        print(f"\n\nSpotify links for {count_updated + count_untouched} out of {total}")
    create_json_file(folder, "failed", failed)




def matching_episode_ids(title, podcast, verbose=False):
    try:
        query = title + " " + podcast
        while len(query) > 100:
            query = query.rsplit(" ", maxsplit=1)[0]
        results = sp.search(q=query, type="episode", limit=10, offset=0, market="US")
    except spotipy.SpotifyException as e:
        print(e.msg, e.reason)
        if e.http_status == 429:
            exit(1)
        return []
    
    matches = []

    for episode in results['episodes']['items']:
        
        spotify_title = episode['name']
        if match_title(title, podcast, spotify_title):
            matches.append(episode['id'])
            if verbose:
                print("✔️ ", episode['name'])
        elif verbose:
            print("X ", episode['name'])

    return matches

def get_episodes(ids):
    try:
        results = sp.episodes(ids, market="US")
    except spotipy.SpotifyException as e:
        print(e.msg)
        if e.http_status == 429:
            exit(1)
        return []
    else:
        return results['episodes']


def match_title(title, podcast, spotify_title):
    # Normalize by lowering case and removing punctuation
    title = title.strip().casefold()
    title = title.translate(str.maketrans('', '', string.punctuation))
    # print(title)
    spotify_title = spotify_title.strip().casefold()
    spotify_title = spotify_title.translate(str.maketrans('', '', string.punctuation))
    # print(spotify_title)
    podcast = podcast.strip().casefold()
    podcast = podcast.translate(str.maketrans('', '', string.punctuation))
    # print(podcast)
    
    # 1. Spotify title is the same as item title
    if title == spotify_title:
        return True
    # 2. Spotify title includes both title of epsiode and name of podcast
    elif title in spotify_title and podcast in spotify_title:
        return True
    
    spotify_title_no_ep = re.sub(RE_EP, "", spotify_title).strip()
    title_no_ep = re.sub(RE_EP, "", title).strip()
    # 3. After removing episode number, Spotify title is the same as item title
    if title == spotify_title_no_ep:
        return True
    # 4. After removing episode number,  Spotify title includes both title of epsiode and name of podcast 
    elif title_no_ep in spotify_title_no_ep and podcast in spotify_title_no_ep:
        return True
    # 
    # if spotify_title.endswith(title):
    #     return True

    return False

def match_podcast(podcast, spotify_podcast, publisher=None):
    podcast = podcast.strip().casefold()
    spotify_podcast = spotify_podcast.strip().casefold()
    publisher = publisher.strip().casefold() if publisher else None
    
    # 1. Spotify's podcast name is same as podcast name
    if podcast == spotify_podcast:
        return True

    if publisher and (spotify_podcast in podcast and publisher in podcast):
        return True

    if podcast.translate(str.maketrans('', '', string.punctuation)) == spotify_podcast.translate(str.maketrans('', '', string.punctuation)):
        return True

    # 2. After removing right-most tagline indicated by " - " 
    #    Spotify's podcast name is same as podcast name
    podcast_no_tag = podcast.rsplit(" - ", maxsplit=1)[0]
    spotify_podcast_no_tag = spotify_podcast.rsplit(" - ", maxsplit=1)[0]
    if podcast_no_tag == spotify_podcast_no_tag:
        return True
    
    # 2. After removing all keywords indicated by " | " 
    #    Spotify's podcast name is same as podcast name
    podcast_no_keys = re.split(RE_NO_KEYWORDS, podcast)[0]
    spotify_podcast_no_keys = re.split(RE_NO_KEYWORDS, spotify_podcast)[0]
    if podcast_no_keys == spotify_podcast_no_keys:
        return True
    
    return False


def search_show(podcast_name, verbose=False):
    try:
        query = podcast_name
        while len(query) > 100:
            query = query.rsplit(" ", maxsplit=1)[0]
        results = sp.search(q=query, type="show", limit=10, offset=0, market="US")
    except spotipy.SpotifyException as e:
        print(e.msg, e.reason)
        if e.http_status == 429:
            exit(1)
        return []
    
    return results['shows']['items']


if __name__=="__main__":
    main()