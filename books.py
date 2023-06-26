import os
import logging
import requests
from urllib import parse
from dotenv import load_dotenv, find_dotenv
from transform_for_db import transform_book
from urllib.parse import urlparse, parse_qs, urlencode

# Get API key from .env
load_dotenv(find_dotenv())
API_KEY = os.getenv('GOOGLEBOOKS_API_KEY')

logger = logging.getLogger('book-log')

def get_googlebooks(payload):
    """
    Generator to make request to Google Books API, yields next page of results
    """

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
        results = [item for item in data.get('items', [])]
        # Yield list of title and url
        # print(f"{startIndex} for {payload['q']}")
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

    final_results = []
    books_results = get_googlebooks(payload)
    for result in books_results:
        # results.extend(result)
        for item in result:
            if item['volumeInfo'].get('description', "") != "":
                final_results.append(item)
        if len(final_results) >= limit:
            books_results.close()

    return final_results
    
def books_search_and_transform(search_term, limit=10):
    search_results = search_googlebooks(search_term, limit)
    db_items = []
    for result in search_results:
        try:
            item = transform_book(result, search_term)
        except Exception as e:
            logger.warning(f"Transform error: {e}")
        else:
            if item:
                db_items.append(item)
    return db_items


def get_googlebooks_volume(book_id):
    if not book_id:
        raise Exception(f"get_googlebooks_volume: Google Books ID not found", book_id)

    google_url = "https://www.googleapis.com/books/v1/volumes/" + book_id
    payload = {
        "key": API_KEY,
    }
    # Make request
    payload_str = urlencode(payload, safe=':+')
    try:
        response = requests.get(google_url, params=payload_str)
        response.raise_for_status()
    except requests.RequestException as e:
        raise Exception(f"Unable to fetch data for Google Books ID {book_id}: {e}")


    data = response.json()
    return data


def extract_book_id(url):
    parsed_url = urlparse(url)
    queries = parse_qs(parsed_url.query)
    book_id = queries.get("id", [None])
    return book_id[0]