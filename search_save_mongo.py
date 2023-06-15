import os
import argparse
import pymongo
import pprint
from pymongo.errors import BulkWriteError
from sys import exit
from dotenv import load_dotenv, find_dotenv
from common import create_json_file, get_search_list
from progress import progress
from books import books_search_and_transform
from podcasts import podcast_eps_search_and_transform
from tedtalks import ted_youtube_search_and_transform
from videos import youtube_search_and_transform
from research import research_search_and_transform
from time import sleep

load_dotenv(find_dotenv())
pp = pprint.PrettyPrinter(depth=6)  

# Connect to MongoDB
MONGO_HOST = os.getenv('MONGO_HOST')
MONGO_PORT = int(os.getenv('MONGO_PORT'))
MONGO_DB = os.getenv('MONGO_DB')
client = pymongo.MongoClient(MONGO_HOST, port=MONGO_PORT)
db = client[MONGO_DB]
collection = db['knowledgeitem_master']

TOTAL_RESULTS = 100

def search_various_sources(search_list, limit=TOTAL_RESULTS):
    
    # Dict containing results of each category
    results = {
        'podcasts': [],
        'research': [],
        'videos': [],
        'tedtalks': [],
        'books': [],
    }
    # List of functions and the category of results they generate
    search_functions = [
        ('podcasts', podcast_eps_search_and_transform),
        ('research', research_search_and_transform),
        ('videos', youtube_search_and_transform),
        ('tedtalks', ted_youtube_search_and_transform),
        ('books', books_search_and_transform),
    ]
    total = len(search_list)
    # Loop through each function
    for type, fn in search_functions:
        # Loop through each search term
        for i, search_term in enumerate(search_list):
            progress(i+1, total, type)
            # Get results
            search_results = fn(search_term, limit)
            # Add results to results list
            if search_results:
                results[type].extend(search_results[:limit])
    return results
        
        
def main():
    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("search_file", help="Path of the text file containing search terms")
    parser.add_argument("-l", "--limit", help="Total results", type=int, default=TOTAL_RESULTS)
    args = parser.parse_args()
    
    # Get search terms from text file at `args.search_time`
    try:
        search_list = get_search_list(args.search_file)
    except Exception as e:
        exit(e)

    results = search_various_sources(search_list=search_list, limit=args.limit)
    
    print("Inserting in MongoDB")
    for type in results:
        # for item in results[type]:
        #     pp.pprint(item)
        #     ir = collection.insert_one(item)
        if len(results[type]) < 1:
            continue            
        try:
            ir = collection.insert_many(results[type])
        except BulkWriteError as bwe:
            pp.pprint(bwe.details)
        else:
            print(
                type.upper(), 
                len(ir.inserted_ids))

        
        


if __name__=="__main__":
    main()