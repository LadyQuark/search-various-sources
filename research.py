import os
import logging
import requests
from urllib import parse
from dotenv import load_dotenv, find_dotenv
from transform_for_db import transform_scopus_item
from sys import exit
from progress import progress

# Get API key from .env
load_dotenv(find_dotenv())
API_KEY = os.getenv('SCOPUS_API_KEY')

logger = logging.getLogger('research-log')

def get_scopus(payload):
    """
    Generator to make request to Scopus API, yields next page of results
    """

    url = "https://api.elsevier.com/content/search/scopus"
    startIndex = 0
    while True:
        # Make request
        try:
            response = requests.get(url, params=payload)
            response.raise_for_status()
        except requests.RequestException as e:
            # Exit application if quota exceeded
            if response.status_code == 429:
                print("Quota exceeded")
                logger.warning("Quota exceeded")
                exit(1)
            logger.warning(f"Unable to search Scopus for {payload['query']}: {e}")
            break  
        # Parse response
        data = response.json()

        entries = data['search-results']['entry']
        results = [item for item in entries]
        # Yield list of title and url
        yield results
        # Increment startIndex, stop if startIndex is beyond total results
        startIndex += int(data['search-results']['opensearch:itemsPerPage'])
        if startIndex >= int(data['search-results']['opensearch:totalResults']): 
            break
        payload['start'] = str(startIndex)


def search_scopus(search_term, limit=10):
    """ 
    Searches Scopus for given search term using Scopus Search API
    https://dev.elsevier.com/documentation/ScopusSearchAPI.wadl
    and outputs list of title and url, default count of 10
    """
    # Construct request URL
    payload = {
        "query": f"TITLE-ABS-KEY({search_term})",
        "apiKey": API_KEY,
        "httpAccept": "application/json",        
    }

    results = []
    scopus_results = get_scopus(payload)
    for i, result in enumerate(scopus_results):
        progress(i+1, limit)
        results.extend(result)
        if len(results) >= limit:
            scopus_results.close()

    return results    


def research_search_and_transform(search_term, limit=10):
    """
    Search Scopus and return transformed results
    """
    search_results = search_scopus(search_term, limit)
    db_items = []
    for result in search_results:
        try:
            item = transform_scopus_item(result, search_term)
        except Exception as e:
            logger.warning(f"Transform error: {e}")
            continue
        
        db_items.append(item)

    return db_items


def get_abstract(doi):
    """ 
    Get and return abstract from Elsevier API for given article with DOI if available
    """

    # Make request
    payload = {
        "apiKey": API_KEY,
        "httpAccept": "application/json",
        "field": "dc:description"
    }
    url = f"https://api.elsevier.com/content/article/doi/{doi}"
    payload_str = parse.urlencode(payload, safe='/.')
    try:
        response = requests.get(url, params=payload_str)
        response.raise_for_status()
    except requests.RequestException as e:
        # Exit application if quota exceeded
        if response.status_code == 429:
            print("QUOTA EXCEEDED")
            logger.warning("Quota exceeded")
            exit(1)
        # print(f"Unable to search abstract for Scopus ID: {doi}: {e}")
        logger.warning(f"Unable to search abstract for Scopus ID: {doi}: {e}")
        return None
      
    # Parse response
    data = response.json()
    try:
        abstract = data['full-text-retrieval-response']['coredata']['dc:description']
    except KeyError as e:
        # print(f"Did not receive abstract for: {doi}: {e}")
        logger.warning(f"Did not receive abstract for: {doi}: {e}")
        return None
    else:
        return abstract    

    # Get response
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Unable to search Scopus for {search_term}: {e}")
        return []

    # Parse Response
    data = response.json()
    entries = data['search-results']['entry']
    results = []
    for entry in entries:
        # Get URL for scopus
        url = None
        for link in entry.get("link", []):
            if link['@ref'] == "scopus":
                url = link['@href']
        # Append to results
        results.append({
            'title': entry.get('dc:title'),
            'url': url,
        })

    return results
