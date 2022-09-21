from sys import exit
import argparse
from videos import search_youtube_channel
from transform_for_db import transform_youtube_item
import logging
from progress import progress
from common import create_json_file, load_existing_json_file, valid_destination
import pprint

logger = logging.getLogger('videos-log')

pp = pprint.PrettyPrinter(depth=6)  
# channel = "UCUgZq9PkDp1xaEivtcfJPSg"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", help="Path of the updated JSON file")
    parser.add_argument("channel", help="ID of channel", type=str)
    parser.add_argument("-v", "--verbose", help="Print results as they come", action="store_true")
    parser.add_argument("-limit", help="Update only first 10 items", type=int, default=0)
    args = parser.parse_args()

    if not valid_destination(args.destination):
        exit(1)

    videos = youtube_channel_and_transform(
        channel=args.channel, 
        limit=None if args.limit <= 0 else args.limit, 
        verbose=args.verbose)

    if len(videos) > 0:
        create_json_file(args.destination, videos[0]['authors'], videos)
    


def youtube_channel_and_transform(channel, limit=None, verbose=False):
    results = search_youtube_channel(
        search_term="", 
        channelId=channel, 
        limit=limit, 
        order="date", 
        verbose=verbose)

    db_items = []
    total = len(results)
    for i, result in enumerate(results):
        if verbose: progress(i+1, total)
        try:
            item = transform_youtube_item(result, search_term=None)
        except Exception as e:
            if verbose: print(f"Transform error: {e}")
            logger.warning(f"Transform error: {e}")
        else:
            db_items.append(item)
    return db_items


if __name__=="__main__":
    main()