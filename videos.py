import os
import requests
from dotenv import load_dotenv, find_dotenv

# Get API key from .env
load_dotenv(find_dotenv())
API_KEY = os.getenv('YOUTUBE_API_KEY')

def get_youtube(payload):
    """ 
    Generator that makes GET request to YouTube Data API v3 with given payload
    https://developers.google.com/youtube/v3/docs/search/list
    and yields list of title and url, iterates over paged results
    """

    url = "https://www.googleapis.com/youtube/v3/search"
    n = 1
    while True:
        # Make request
        try:
            print(f"Getting page {n}")
            response = requests.get(url, params=payload)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"Unable to search YouTube for {payload['q']}: {e}")
            break
        # Parse response
        data = response.json()
        results = []
        for item in data['items']:
            results.append({
                'title': item['snippet']['title'],
                'url': f"https://www.youtube.com/watch?v={item['id']['videoId']}",
            })
        # Yield list of title and url
        yield results
        # Get token for next page if it exists, else stop
        if "nextPageToken" not in data: 
            break
        payload['pageToken'] = data['nextPageToken']
        n += 1
     
def search_youtube(search_term, limit=10, country="US", lang="en"):
    """ 
    Searches YouTube for given search term
    and outputs list of title and url, default count of 10
    Results change according to given country (ISO 3166-1 alpha-2 country code)
    and language (ISO 639-1 two-letter language code)
    """
    #TODO: Check if country and language are valid

    # Construct request URL
    payload = {
        "part": "snippet",
        "type": "video",
        "q": requests.utils.quote(search_term),
        "key": API_KEY,
        "maxResults": min(limit, 50),
        "regionCode": country,
        "relevanceLanguage": lang,
    }

    results = []
    youtube_results = get_youtube(payload)
    for result in youtube_results:
        results.extend(result)
        if len(results) >= limit:
            youtube_results.close()
    
    return results


def search_youtube_ted(search_term, limit=10):
    """ 
    Searches TED channel on YouTube for given search term
    and outputs list of title and url, default count of 10
    """
    #TODO: Check if country and language are valid

    # Construct request URL
    payload = {
        "part": "snippet",
        "type": "video",
        "channelId": "UCAuUUnT6oDeKwE6v1NGQxug",
        "q": requests.utils.quote(search_term),
        "key": API_KEY,
        "maxResults": min(limit, 50),
    }

    results = []
    youtube_results = get_youtube(payload)
    for result in youtube_results:
        results.extend(result)
        if len(results) >= limit:
            youtube_results.close()
    
    return results

