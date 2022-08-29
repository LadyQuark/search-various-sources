import os
import logging
import requests
from urllib import parse
from dotenv import load_dotenv, find_dotenv
from transform_for_db import transform_book_item

# Get API key from .env
load_dotenv(find_dotenv())
API_KEY = os.getenv('GOOGLEBOOKS_API_KEY')

logger = logging.getLogger('book-log')

def get_googlebooks(payload):
    url = "https://www.googleapis.com/books/v1/volumes"
    startIndex = 0
    while True:
        # Make request
        payload_str = parse.urlencode(payload, safe=':+')
        try:
            response = requests.get(url, params=payload_str)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"Unable to search Google Books for {payload['q']}: {e}")
            logger(f"Unable to search Google Books for {payload['q']}: {e}")
            break    
        # Parse response
        data = response.json()
        results = [item for item in data['items']]
        # Yield list of title and url
        print(f"{startIndex} for {payload['q']}")
        yield results
        # Increment startIndex, stop if startIndex is beyond total results
        startIndex += payload["maxResults"]
        if startIndex >= data["totalItems"]: 
            break
        payload['startIndex'] = startIndex

def search_googlebooks(search_term, limit=10):
    """ 
    Searches Google Books for given search term using Google API 
    https://developers.google.com/books/docs/v1/using#auth
    and outputs list of title and url, default count of 10
    """

    # Construct query
    payload = {
        "q": search_term,
        "key": API_KEY,
        "maxResults": min(limit, 40),
    }

    results = []
    books_results = get_googlebooks(payload)
    for result in books_results:
        results.extend(result)
        if len(results) >= limit:
            books_results.close()

    return results
    
def books_search_and_transform(search_term, limit=10):
    search_results = search_googlebooks(search_term, limit)
    db_items = []
    for result in search_results:
        try:
            item = transform_book_item(result, search_term)
        except Exception as e:
            logger.warning(f"Transform error: {e}")
        else:
            db_items.append(item)
    return db_items