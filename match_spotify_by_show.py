import os
import csv
import argparse
import spotipy
from common import create_json_file, load_existing_json_file, valid_source_destination, get_search_list
from dotenv import load_dotenv, find_dotenv
from match_spotify import match_title, search_show, match_podcast, get_show_episodes
from transform_for_db import add_spotify_data
from progress import progress
from spotipy.oauth2 import SpotifyClientCredentials

shows_file = os.path.join("db", "spotify_show_ids.csv")

# Get API key from .env
load_dotenv(find_dotenv())
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID,
                                                           client_secret=SPOTIFY_CLIENT_SECRET))

def main():
    # Parse and check arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--txt", help="Path to file containing search terms", type=str)
    parser.add_argument("--source", help="Path to db items", type=str)
    parser.add_argument("-v", "--verbose", help="Print results as they come", action="store_true")
    parser.add_argument("-f", "--fuzzy", help="Match episodes whose date match but titles do not match", action="store_true")
    args = parser.parse_args()

    # If running to just identify Spotify IDs for a list of podcasts and storing the same
    if args.txt:
        search_list = get_search_list(args.txt)
        for name in search_list:
            find_and_store_show_id(name)
        exit(0)

    elif not args.source:
        print("Pass either text file containing podcast names with '-txt'", 
            "or JSON file of a single podcast to be updated with '-source'")
        exit(1)

    # If running to update a JSON file containing db items of a single podcast to be updated
    
    # Check path and get source file
    destination_folder = os.path.join(os.path.dirname(args.source), "updated")
    if not valid_source_destination(args.source, destination_folder, file_ext=".json"):
        exit(1)
    destination_file = os.path.basename(args.source)
    destination = os.path.join(destination_folder, destination_file)
    podcast_episodes = load_existing_json_file(None, None, args.source)
    total = len(podcast_episodes)
    failed = []
    fuzzy = []
    
    # Get podcast name
    podcast_name = podcast_episodes[0]['metadata']['podcast_title']
    if args.verbose: print("Updating Spotify links for", podcast_name)
    
    # Check if Spotify ID already stored for name
    with open(shows_file) as csvfile:
        reader = csv.DictReader(csvfile)
        spotify_id = next((row['id'] for row in reader if row['name'] == podcast_name), None)
    # Else search for Spotify ID
    if not spotify_id:
        spotify_id = find_and_store_show_id(podcast_name, args.verbose)
        # Quit if not found
        if not spotify_id:
            print("Could not load Spotify ID")
            exit(1)

    # Get all episodes of show with id `spotify_id`
    if args.verbose: print(spotify_id)
    spotify_episodes = []
    episodes = get_show_episodes(spotify_id, args.verbose)
    for episode_set in episodes:
        spotify_episodes.extend(episode_set)
    create_json_file("test", "spotify_eps", spotify_episodes)

    # Match podcast_episodes with spotify_episodes
    count_matched = 0
    count_untouched = 0
    for n, item in enumerate(podcast_episodes):
        episode_title = item["title"]
        links = item['metadata'].setdefault('additional_links', {})
        links.setdefault('spotify_url', None)
        progress(n, total, episode_title)

        # Check if field already exists
        if links.get('spotify_url') and links['spotify_url'] != "":
            count_untouched += 1
            print("No need to update")
            continue

        # Check with each episode in spotify_episodes
        matched = False
        for episode in spotify_episodes:
            
            if match_title(episode_title, podcast_name, episode['name']):
                # Update spotify link                
                item = add_spotify_data(item, episode) 
                matched = True
                count_matched += 1
                if args.verbose: print(f"\n{episode_title} -> {episode['name']}")
                break
            
            elif args.fuzzy and item["publishedDate"] == episode["release_date"]:
                item = add_spotify_data(item, episode) 
                fuzzy.append(item)
                matched = True
                count_matched += 1
                if args.verbose: print(f"\n{episode_title} -> {episode['name']}")
                if args.verbose: print("Matched by date not title")
                break
        
        if not matched:
            failed.append(item)
            if args.verbose: print("No matches found!")  

    if count_matched > 0:
        create_json_file(destination_folder, destination_file, podcast_episodes)
        print(f"\n\nSpotify links for {count_matched + count_untouched} out of {total}")
    create_json_file(destination_folder, "failed", failed)
    create_json_file(destination_folder, "fuzzy_matches", fuzzy)


def find_and_store_show_id(name, verbose=False):
    try:
        results = search_show(name)
    except Exception as e:
        exit(1)
            
    for item in results:
        if match_podcast(name, item['name'], item['publisher']):
            if verbose:
                print("✔️ ", item['name'])
            with open(shows_file, 'a') as f:
                w = csv.DictWriter(f, {'name', 'id'})
                w.writerow({'name': name, 'id': item['id']})
            return item['id']
        elif verbose:
            print("X ", item['name'])

    return None






if __name__=="__main__":
    main()