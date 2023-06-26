""" 
Searches for terms in text file passed as an argument
in Apple Podcasts, Scopus, YouTube, TED talks and Google Books
saves JSON files for each type in folder `ki_json` 
default number of results per type is 50
"""

import os
import argparse
from common import create_json_file, get_search_list
from podcasts import podcast_eps_search_and_transform
from research import research_search_and_transform
from videos import youtube_search_and_transform
from tedtalks import ted_youtube_search_and_transform
from books import books_search_and_transform
from sys import exit
from progress import progress

TOTAL_RESULTS = 50

def main():
    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("search_file", help="Path of the text file containing search terms")
    parser.add_argument("-l", "--limit", help="Total results", type=int, default=TOTAL_RESULTS)
    parser.add_argument("-f", "--folder", help="Destination folder", type=str, default='ki_json')
    args = parser.parse_args()
    
    # Get search terms from text file at `args.search_time`
    try:
        search_list = get_search_list(args.search_file)
        total = len(search_list)
    except Exception as e:
        print(e)
        exit(1)
    
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
    folder_name = os.path.join(args.folder, os.path.basename(args.search_file).replace(".txt", ""))
    # Loop through each function
    for type, fn in search_functions:
        # Loop through each search term
        for i, search_term in enumerate(search_list):
            # progress(i+1, total, type)
            # Get results
            try:
                search_results = fn(search_term, args.limit)
            except Exception as e:
                print("FATAL ERROR:", e)
            else:
                # Add results to results list
                print('{:<10s} {:<20s} {:<3s}'.format( type.upper(), search_term, str(len(search_results)) ))
                results[type].extend(search_results)
        # Create json file for each category of results
        create_json_file(
            folder=folder_name, name=type, source_dict=results[type]
        )
        
        


if __name__=="__main__":
    main()