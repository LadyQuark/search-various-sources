import os
import requests
from dotenv import load_dotenv, find_dotenv

# Get API key from .env
load_dotenv(find_dotenv())
API_KEY = os.getenv('YOUTUBE_API_KEY')
     
def search_youtube(search_term, limit=10, country="US", lang="en"):
    """ 
    Searches YouTube for given search term using YouTube Data API v3 
    https://developers.google.com/youtube/v3/docs/search/list
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
        "maxResults": limit,
        "regionCode": country,
        "relevanceLanguage": lang,
    }
    url = "https://www.googleapis.com/youtube/v3/search"
    # Get response
    try:
        response = requests.get(url, params=payload)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Unable to search YouTube for {search_term}: {e}")
        return []
    # Parse response
    data = response.json()
    items = data['items']
    results = []
    for item in items:
        results.append({
            'title': item['snippet']['title'],
            'url': f"https://www.youtube.com/watch?v={item['id']['videoId']}",
        })   
    return results
