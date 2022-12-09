import os
import argparse
import pprint
from common import get_search_list
import match_spotify
import podcasts
from progress import progress
from time import sleep
from sys import exit

pp = pprint.PrettyPrinter(depth=6)                                               

def main():
    # Parse and check arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--destination", help="Path to destination folder", default="ki_json")
    parser.add_argument("-f", "--file", help="Path to text file of podcast names or URLS")
    parser.add_argument("-u", "--url", help="URL to podcast")
    parser.add_argument("-n", "--name", help="Name of podcast")
    parser.add_argument("-v", "--verbose", help="Print results as they come", action="store_true")
    # parser.add_argument("-z", "--fuzzy", help="Make fuzzy matches (by release date)", action="store_true")
    # parser.add_argument("-l", "--delay", help="Delay searches because of rate limits", action="store_true")
    args = parser.parse_args()

    if args.file:
        try:
            podcast_list = get_search_list(args.source)
        except Exception as e:
            exit(e)
    elif args.url:
        if "podcasts.apple.com" in args.url or "open.spotify.com" in args.url:
            podcast_list = [args.url]
        else:
            exit("Invalid URL")
    elif args.name:
        podcast_list = [args.name]
    else:
        exit("all_episodes_podcast.py: error: one of the following arguments are required: file, url, name")

    for query in podcast_list:
        if "open.spotify.com" in query:
            match_spotify.save_all_episodes_podcast_and_transform(
                url=args.url,
                podcast_name=None,
                folder=args.destination,
                verbose=args.verbose
            )
        else:
            podcasts.save_all_episodes_podcast_and_transform(
                query=query,
                folder=args.destination,
                verbose=args.verbose
            )



if __name__=="__main__":
    main()