import os
from books import books_search_and_transform
from common import create_json_file
from podcasts import podcast_eps_search_and_transform
from sys import argv, exit

from videos import youtube_search_and_transform

TOTAL_RESULTS = 100

def main():
    if len(argv) != 2:
        exit(1)
    filename = "search_terms/" + argv[1]
    try:
        search_list = get_search_list(filename)
    except Exception as e:
        print(e)
        exit(1)

    n = 0
    total = len(search_list)
    results = []
    for search_term in search_list:
        n += 1
        print(f"{n}/{total}")        
        # search_results = podcast_eps_search_and_transform(search_term, TOTAL_RESULTS)
        search_results = youtube_search_and_transform(search_term, TOTAL_RESULTS)
        results.extend(search_results)
    
    name = argv[1].replace(".txt", "")
    create_json_file(
        folder="ki_json/videos", name=name, source_dict=results
    )

def get_search_list(filename):
    # Check file ends with `.txt`
    if not filename.endswith(".txt"):
        raise Exception("File name should end in .txt")
    
    # Make path
    try:
        filepath = os.path.join(filename)
    except Exception as e:
        raise Exception(e)

    # Check path exists
    if not os.path.isfile(filepath):
        raise Exception(f"Could not find file {filepath}")

    with open(filepath, 'r') as f:
        search_list = [line.strip() for line in f.readlines()]

    return search_list

if __name__=="__main__":
    main()