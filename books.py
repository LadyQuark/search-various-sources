import json
import os
import requests
import urllib.parse
from dotenv import load_dotenv, find_dotenv

# Get API key from .env
load_dotenv(find_dotenv())
API_KEY = os.getenv('GOOGLEBOOKS_API_KEY')
     

def search_googlebooks(search_term, limit=10):
    query = urllib.parse.quote(search_term)
    url = f"https://www.googleapis.com/books/v1/volumes?q={query}&key={API_KEY}&maxResults={limit}"

    # Get response
    try:
        response = requests.get(url)
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