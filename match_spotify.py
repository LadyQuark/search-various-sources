import os
import argparse
import pprint
import string
import re
import random
import spotipy
from common import create_json_file, load_existing_json_file, valid_source_destination, standard_date
from dotenv import load_dotenv, find_dotenv
from progress import progress
from spotipy.oauth2 import SpotifyClientCredentials
from urllib.parse import urlparse
from transform_for_db import transform_spotify, add_itunes_data
import podcasts
from time import sleep
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
SPOTIFY_MARKET = "US"                                            

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
    if args.limit > 0 and args.limit < total:
        podcast_episodes = random.choices(podcast_episodes, k=args.limit)
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
        links = item['metadata'].setdefault('additional_links', {})

        # If field already exists, move to next item
        if links.get('spotify_url') and links['spotify_url'] != "":
            count_untouched += 1
            if args.verbose: print("No need to update")
            continue
        
        # Find URL and update
        try:
            episode = find_spotify_episode(title, podcast, args.verbose)
        except Exception:
            # Stop loop and save results so far
            failed.append(item) 
            break
        if episode:
            url = episode['external_urls']['spotify']                  
            links.setdefault('spotify_url', url)
            item['original'].append(episode)
            count_updated += 1
            break
        
        failed.append(item) 
        if args.verbose: print("No matches found!")


    # Create JSON files
    folder = os.path.dirname(args.destination) if args.destination.endswith(".json") else args.destination
    file_name = os.path.basename(args.destination) if args.destination.endswith(".json") else "updated_podcasts"
    create_json_file(folder, file_name, podcast_episodes)
    print(f"\n\nSpotify links for {count_updated + count_untouched} out of {total}")
    if count_updated > 0:
        create_json_file(folder, file_name, podcast_episodes)
        print(f"\n\nSpotify links for {count_updated + count_untouched} out of {total}")
    create_json_file(folder, "failed", failed)


def find_spotify_episode(title, podcast, verbose=False):
    """ 
    Searches Spotify for podcast episode with given title and podcast name
    accounts for some variation in titles and podcast names
    returns matching episode object from Spotify
    """
    if verbose:
        action_str = f"Searching for: {title} | {podcast}"
        print("\n", action_str)
        print("-" * len(action_str))
    
    # Get full info of episodes with matching titles
    try:
        matching_ids = matching_episode_ids(title, podcast, verbose)
        matching_episodes = get_episodes(matching_ids) if len(matching_ids) > 0 else []
    except Exception as e:
        raise Exception(e)
    
    # For each matching episode, check podcast name
    for episode in matching_episodes:
        # url = episode['external_urls']['spotify']
        title_spotify = episode['name']
        podcast_spotify = episode['show']['name']
        publisher = episode['show']['publisher']

        if verbose: print(title_spotify, " | ", podcast_spotify)

        # If podcast name matches, update item and stop checking for this item
        if match_podcast(podcast, podcast_spotify, publisher):
            if verbose: print("Found it!")
            return episode
    
    return None


def matching_episode_ids(title, podcast, verbose=False):
    """ 
    Searches Spotify for podcast with given title and podcast name,
    accounts for some variation in episode title,
    returns list of Spotify IDs of episodes that are possible matches
    """

    try:
        # Better results when searching for both episode and podcast names
        query = title + " " + podcast
        # Restrict query to 100 characters by removing full words
        while len(query) > 100:
            query = query.rsplit(" ", maxsplit=1)[0]
        # Get results
        results = sp.search(q=query, type="episode", limit=10, offset=0, market=SPOTIFY_MARKET)
    except spotipy.SpotifyException as e:
        print(e.msg, e.reason)
        if e.http_status == 429:
            raise Exception("Spotify Quota Exceeded")
        return []
    
    # Loop through list and make list of possible matches
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
    """ 
    Get episode objects from Spotify for each id
    """
    try:
        results = sp.episodes(ids, market=SPOTIFY_MARKET)
    except spotipy.SpotifyException as e:
        print(e.msg)
        if e.http_status == 429:
            raise Exception("Spotify Quota Exceeded")
        return []
    else:
        return results['episodes']


def match_title(title, podcast, spotify_title):
    """ Match episode titles accounting for subtle differences """

    # Normalize by lowering case and removing punctuation
    title = title.strip().casefold()
    title = title.translate(str.maketrans('', '', string.punctuation))
    spotify_title = spotify_title.strip().casefold()
    spotify_title = spotify_title.translate(str.maketrans('', '', string.punctuation))
    podcast = podcast.strip().casefold()
    podcast = podcast.translate(str.maketrans('', '', string.punctuation))
    
    # 1. Spotify title is the same as item title
    if title == spotify_title:
        return True
    # 2. Spotify title includes both title of epsiode and name of podcast
    elif title in spotify_title and podcast in spotify_title:
        return True
    
    # Remove episode numbers from titles
    spotify_title_no_ep = re.sub(RE_EP, "", spotify_title).strip()
    title_no_ep = re.sub(RE_EP, "", title).strip()
    # 3. After removing episode number, Spotify title is the same as item title
    if title == spotify_title_no_ep:
        return True
    # 4. After removing episode number, Spotify title includes both title of epsiode and name of podcast 
    elif title_no_ep in spotify_title_no_ep and podcast in spotify_title_no_ep:
        return True


    return False


def match_podcast(podcast, spotify_podcast, publisher=None):
    """ Match podcast names accounting for subtle differences """
    
    # Normalize by lowering case
    podcast = podcast.strip().casefold()
    spotify_podcast = spotify_podcast.strip().casefold()
    publisher = publisher.strip().casefold() if publisher else None
    
    # 1. Spotify's podcast name is same as podcast name
    if podcast == spotify_podcast:
        return True
    # 2. Podcast name includes Spotify's podcast name and publisher
    if publisher and (spotify_podcast in podcast and publisher in podcast):
        return True
    # 3. After removing punctuation, Spotify's podcast name is same as podcast name
    if podcast.translate(str.maketrans('', '', string.punctuation)) == spotify_podcast.translate(str.maketrans('', '', string.punctuation)):
        return True

    # 4. After removing right-most tagline indicated by " - " 
    #    Spotify's podcast name is same as podcast name
    podcast_no_tag = podcast.rsplit(" - ", maxsplit=1)[0]
    spotify_podcast_no_tag = spotify_podcast.rsplit(" - ", maxsplit=1)[0]
    if podcast_no_tag == spotify_podcast_no_tag:
        return True
    
    # 5. After removing all keywords indicated by " | " 
    #    Spotify's podcast name is same as podcast name
    podcast_no_keys = re.split(RE_NO_KEYWORDS, podcast)[0]
    spotify_podcast_no_keys = re.split(RE_NO_KEYWORDS, spotify_podcast)[0]
    if podcast_no_keys == spotify_podcast_no_keys:
        return True
    
    return False


def search_show(podcast_name, verbose=False):
    """ 
    Searches Spotify for podcast with given podcast name,
    returns results
    """
    try:
        query = podcast_name
        while len(query) > 100:
            query = query.rsplit(" ", maxsplit=1)[0]
        results = sp.search(q=query, type="show", limit=10, offset=0, market=SPOTIFY_MARKET)
    except spotipy.SpotifyException as e:
        print(e.msg, e.reason)
        if e.http_status == 429:
            raise Exception("Spotify Quota Exceeded")
        return []
    
    return results['shows']['items']

def find_spotify_show(name, verbose=False):
    try:
        results = search_show(name)
    except Exception as e:
        exit(1)
            
    for item in results:
        if match_podcast(name, item['name'], item['publisher']):
            if verbose: print("✔️ ", item['name'])
            return item
        elif verbose:
            print("X ", item['name'])

    return None

def get_show_episodes(show_id, verbose=False):
    offset = 0
    while True: 
        try:
            results = sp.show_episodes(show_id=show_id, limit=50, offset=offset, market=SPOTIFY_MARKET)
        except spotipy.SpotifyException as e:
            print(e.msg, e.reason)
            if e.http_status == 429:
                exit(1)
            break
        yield results['items']

        offset += 50
        if offset >= results['total']:
            break


def save_all_episodes_podcast_and_transform(url, podcast_name, folder="ki_json", verbose=False, fetch_itunes=True):
    """
    1. Gets show ID from `url`
    2. Gets info about show from `podcast_name`
    3. Gets all episodes of show
    4. Transforms all episodes
    If `fetch_itunes`:
        5. Searches for show in iTunes
        6. Gets all episodes for iTunes show and metadata for show
        7. For each transformed Spotify metadata: 
            a. match with iTunes episode and adds iTunes data
            b. if no match, search iTunes for episode
    """

    parsed_url = urlparse(url)
    split_path = parsed_url.path.rsplit("/", maxsplit=1)
    if len(split_path) != 2:
        raise Exception("No Spotify ID found in URL")
    if split_path[0] != "/show":
        raise Exception("Spotify URL not for podcast show")
    spotify_id = split_path[1]

    try:
        spotify_show = sp.show(spotify_id, market=SPOTIFY_MARKET)
        podcast_name = spotify_show['name']
        print(podcast_name)
    except spotipy.SpotifyException as e:
        raise Exception("Could not fetch spotify show ID#", spotify_id)
    
    spotify_episodes = []
    for episode_set in get_show_episodes(spotify_id, verbose):
        spotify_episodes.extend(episode_set)

    episodes = []
    fuzzy = []
    failed = []
    
    for item in spotify_episodes:
        episode = transform_spotify(item, search_term=None, metadata=spotify_show)
        if episode:
            episodes.append(episode)
    
    total = len(episodes)

    if fetch_itunes:

        itunes_podcast = podcasts.search_podcasts(search_term=podcast_name, limit=5, search_type="podcast")
        if itunes_podcast:
            itunes_podcast = itunes_podcast[0]
            itunes_id = itunes_podcast['collectionId']
            itunes_episodes = podcasts.itunes_lookup_podcast(itunes_id)
            show = next((item for item in itunes_episodes if item["kind"] == "podcast"), {})
            metadata = podcasts.scrape_itunes_metadata(itunes_id, show)

            for i, item in enumerate(episodes):
                # progress(i + 1, total)
                episode_title = item["title"]
                count_matched = 0
                if verbose: print(episode_title)
                item['metadata']['podcast_id']['itunes_id'] = itunes_id

                
                for itunes in itunes_episodes:
                    if itunes["wrapperType"] != "podcastEpisode":
                        continue

                    try:
                        if match_title(episode_title, podcast_name, itunes['trackName']):
                            item = add_itunes_data(item, itunes, metadata)            
                            matched = True
                            count_matched += 1
                            if verbose: print(f"\n{episode_title} -> {itunes['trackName']}")
                            break
                            
                        elif item["publishedDate"] == standard_date(itunes["releaseDate"]):
                            item = add_itunes_data(item, itunes, metadata) 
                            matched = True
                            fuzzy.append(item)
                            count_matched += 1
                            if verbose: print(f"\n{episode_title} -> {itunes['trackName']}")
                            if verbose: print("Matched by date not title")
                            break
                    except Exception as e:
                        print(e.__class__.__name__, e)
                        pp.pprint(itunes)
                        pp.pprint(item)
                        exit(1)
                    
                if not matched:
                    query = episode_title
                    while len(query) > 100:
                        query = query.rsplit(" ", maxsplit=1)[0]
                    try:
                        if verbose: print("\nSearching iTunes by title")
                        results = podcasts.search_podcasts(query, attribute="titleTerm")
                        sleep(5)
                    except Exception as e:
                        print(e)
                        failed.append(item)
                    else:
                        for result in results:
                            # Update `additional_links` and stop loop
                            if result['collectionId'] == itunes_id:                  
                                item = add_itunes_data(item, result, metadata) 
                                count_matched += 1
                                matched = True
                                break

                    if not matched:
                        failed.append(item)
                        if verbose: print("No matches found!")
        else:
            print(f"iTunes: No matching podcast with name {podcast_name} found")

        create_json_file(folder=folder, name="itunes_failed", source_dict=failed)
        create_json_file(folder=folder, name="itunes_fuzzy_matches", source_dict=fuzzy)

    create_json_file(folder=folder, name=podcast_name, source_dict=episodes)


if __name__=="__main__":
    main()