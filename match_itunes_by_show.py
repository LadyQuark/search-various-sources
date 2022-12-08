import os
import argparse
import pprint
from common import create_json_file, load_existing_json_file, valid_existing_file, valid_source_destination
from podcasts import search_podcasts
from progress import progress
from time import sleep
from sys import exit

pp = pprint.PrettyPrinter(depth=6)                                               

def main():
    # Parse and check arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("source", help="Path to db items")
    parser.add_argument("-v", "--verbose", help="Print results as they come", action="store_true")
    parser.add_argument("-d", "--delay", help="Delay searches because of rate limits", action="store_true")
    args = parser.parse_args()

    # Check path and get source file
    destination_folder = os.path.join(os.path.dirname(args.source), "updated")
    destination_file = os.path.basename(args.source)
    destination = os.path.join(destination_folder, destination_file)
    if not valid_existing_file(args.source, ".json") or not valid_source_destination(args.source, destination, file_ext=".json"):
        exit(1)
    podcast_episodes = load_existing_json_file(None, None, args.source)
    total = len(podcast_episodes)
    failed = []
    fuzzy = []

    # Get podcast name and ID
    podcast_name = podcast_episodes[0]['metadata']['podcast_title']
    podcast_id = find_podcast_id(podcast_episodes)
    if not podcast_id:
        print("Could not find podcast ID")
        exit(1)
    if args.verbose: print("Updating iTunes links for", podcast_name, podcast_id)

    # For each podcast_episodes search for corresponding iTunes episode
    count_matched = 0
    count_untouched = 0
    for n, item in enumerate(podcast_episodes):
        episode_title = item["title"]
        links = item['metadata'].setdefault('additional_links', {})
        links.setdefault('spotify_url', None)
        links.setdefault('itunes_url', None)        
        progress(n, total, episode_title)

        # Check if field already exists
        if links.get('itunes_url') and links['itunes_url'] != "":
            count_untouched += 1
            continue
        
        # Search Apple iTunes Podcasts
        matched = False
        query = episode_title
        while len(query) > 100:
            query = query.rsplit(" ", maxsplit=1)[0]
        try:
            results = search_podcasts(query, attribute="titleTerm")
            if args.delay: sleep(5)
        except Exception as e:
            print(e)
            failed.append(item)
            break
        else:
            # Find matching result
            for result in results:
                # Update `additional_links` and stop loop
                if result['trackName'] == episode_title and result['collectionId'] == podcast_id:                  
                    links['itunes_url'] = result['trackViewUrl']
                    count_matched += 1
                    matched = True
                    break
            if matched: continue
        # Note all episodes with no matches
        failed.append(item)
        if args.verbose: print("No matches found!")  

    # Create output files

    create_json_file(destination_folder, destination_file, podcast_episodes)
    print(f"\n\niTunes links for {count_matched + count_untouched} out of {total}")
    create_json_file(destination_folder, "failed", failed)
    create_json_file(destination_folder, "fuzzy_matches", fuzzy)    



def find_podcast_id(podcast_episodes):
    for item in podcast_episodes:
        if "collectionId" in item:
            return item['collectionId']
    return None



if __name__=="__main__":
    main()