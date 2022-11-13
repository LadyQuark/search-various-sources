import os
import logging
import requests
from urllib import parse
from dotenv import load_dotenv, find_dotenv
from transform_for_db import transform_youtube_item
from progress import progress

# Get API key from .env
load_dotenv(find_dotenv())
API_KEY = os.getenv('YOUTUBE_API_KEY')
MAX_RESULTS = 50

logger = logging.getLogger('videos-log')

def get_youtube(payload, verbose=False, url_path="search"):
    """ 
    Generator that makes GET request to YouTube Data API v3 with given payload
    https://developers.google.com/youtube/v3/docs/search/list
    and yields list of title and url, iterates over paged results
    """

    url = "https://www.googleapis.com/youtube/v3/" + url_path
    n = 1
    while True:
        # Make request
        payload_str = parse.urlencode(payload, safe=':+')
        try:
            # if verbose: print("Getting page ", n)
            response = requests.get(url, params=payload_str)
            response.raise_for_status()
        except requests.RequestException as e:
            if verbose: print(f"Unable to search YouTube for {payload['q']}: {e}")
            logger.warning(f"Unable to search YouTube for {payload['q']}: {e}")
            break
        # Parse response
        data = response.json()
        results = [item for item in data['items']]
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
        "q": search_term,
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


def youtube_search_and_transform(search_term, limit=10):
    search_results = search_youtube(search_term, limit)
    db_items = []
    for result in search_results:
        try:
            item = transform_youtube_item(result, search_term)
        except Exception as e:
            logger.warning(f"Transform error: {e}")
        else:
            db_items.append(item)
    return db_items


def search_youtube_channel(search_term, channelId, limit=10, order="relevance", verbose=False):
    """ 
    Searches TED channel on YouTube for given search term
    and outputs list of title and url, default count of 10
    """
    #TODO: Check if country and language are valid

    # Construct request URL
    payload = {
        "part": "snippet",
        "type": "video",
        "channelId": channelId,
        "q": search_term,
        "key": API_KEY,
        "maxResults": min(limit, 50) if limit else 50,
        "order": order
    }

    results = []
    youtube_results = get_youtube(payload, verbose)
    for result in youtube_results:
        results.extend(result)
        if limit and len(results) >= limit:
            youtube_results.close()
    
    return results


def youtube_videos_stats(ids, verbose=False):
    
    if isinstance(ids, list):
        ids = ",".join(ids)
            
    # Construct request URL
    payload = {
        "part": "snippet,statistics",
        "id": ids,
        "maxResults": MAX_RESULTS,
        "key": API_KEY,
    }
    results = []
    youtube_results = get_youtube(payload, verbose=verbose, url_path="videos")
    for result in youtube_results:
        results.extend(result)
    
    return results