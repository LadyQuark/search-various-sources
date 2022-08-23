import json
import os
import requests
import urllib.parse
import pprint

def main():
    pp = pprint.PrettyPrinter(depth=4)
    results = search_podcasts(search_term="apple", 
        search_type="podcastEpisode", limit=2)
    pp.pprint(results)        
    results = search_podcasts(search_term="apple", 
        search_type="podcast", limit=2)
    pp.pprint(results)

def search_podcasts(search_term, search_type="podcastEpisode", limit=10):
    if search_type not in ["podcast", "podcastEpisode"]:
        print("Invalid search type")
        return None
    
    podcast_list = []
    
    # Query for podcast info using iTunes Search API
    url = f'https://itunes.apple.com/search?term={urllib.parse.quote(search_term)}&media=podcast&entity={search_type}&limit={limit}'
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException:
        print(f"Failed for {search_term}")
        return None
    
    # Parse response
    try:
        data = response.json()
        # Check result count
        results = data['results']
        for item in results:
            # Add RSS feed URL to list `podcast_feeds`
            podcast_list.append({
                'feedUrl': item['feedUrl'] if 'feedUrl' in item else None,
                'podcastName': item['collectionName'],
                'podcastUrl': item['collectionViewUrl'],
                'trackName': item['trackName'],
                'trackUrl': item['trackViewUrl'],
            })

    except Exception as e:
        # If parsing fails, log & move to next podcast name
        print(f"Failed parsing {search_term}")
        print(e)
        # print(data)
        return podcast_list
    
    return podcast_list

if __name__=="__main__":
    main()