import os
import requests
from dotenv import load_dotenv, find_dotenv

# Get API key from .env
load_dotenv(find_dotenv())
API_KEY = os.getenv('GOOGLEBOOKS_API_KEY')
     

def search_googlebooks(search_term, limit=10):
    payload = {
        "q": requests.utils.quote(search_term),
        "key": API_KEY,
        "maxResults": limit,
    }
    url = "https://www.googleapis.com/books/v1/volumes"

    # Get response
    try:
        response = requests.get(url, params=payload)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Unable to search Google Books for {search_term}: {e}")
        return []

    data = response.json()

    items = data['items']
    results = []
    for item in items:
        results.append({
            'title': item['volumeInfo']['title'],
            'url': item['selfLink'],
        })

    return results