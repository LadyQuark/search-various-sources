import os
import argparse
import pprint
from common import create_json_file, get_search_list
from podcasts import save_all_episodes_podcast_and_transform
from progress import progress
from time import sleep
from sys import exit

pp = pprint.PrettyPrinter(depth=6)                                               

def main():
    # Parse and check arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("source", help="Path to text file of podcast names")
    parser.add_argument("destination", help="Path to destination folder", default="ki_json")
    parser.add_argument("-v", "--verbose", help="Print results as they come", action="store_true")
    parser.add_argument("-d", "--delay", help="Delay searches because of rate limits", action="store_true")
    args = parser.parse_args()

    try:
        podcast_list = get_search_list(args.source)
    except Exception as e:
        print(e)
        exit(1)

    
    save_all_episodes_podcast_and_transform(podcast_list, args.destination, args.verbose)



if __name__=="__main__":
    main()