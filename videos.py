import os
import requests
import urllib.parse
from dotenv import load_dotenv, find_dotenv

# Get API key from .env
load_dotenv(find_dotenv())
API_KEY = os.getenv('YOUTUBE_API_KEY')
     
def search_youtube(search_term, limit=10, country="US", lang="en"):
    # Construct request URL
    query = urllib.parse.quote(search_term)
    params = {
        "part": "snippet",
        "type": "video",
        "q": query,
        "key": API_KEY,
        "maxResults": limit,
        "regionCode": country,
        "relevanceLanguage": lang,
    }
    url = "https://www.googleapis.com/youtube/v3/search"
    # Get response
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Unable to search YouTube for {search_term}: {e}")
        return []

    data = response.json()

    items = data['items']
    results = []
    for item in items:
        results.append({
            'title': item['snippet']['title'],
            'url': f"https://www.youtube.com/watch?v={item['id']['videoId']}",
        })   
    return results
