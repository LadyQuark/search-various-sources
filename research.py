import json
import os
import requests
import urllib.parse
from dotenv import load_dotenv, find_dotenv

# Get API key from .env
load_dotenv(find_dotenv())
API_KEY = os.getenv('SCOPUS_API_KEY')
     

def search_scopus(search_term, limit=10):
    # Construct request URL
    query = urllib.parse.quote(search_term)
    url = f"https://api.elsevier.com/content/search/scopus?query=all({query})&apiKey={API_KEY}&httpAccept=application%2Fjson&count={limit}"

    # Get response
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Unable to search Scopus for {search_term}: {e}")
        return 

    data = response.json()

    entries = data['search-results']['entry']
    results = []
    for entry in entries:
        url = None
        for link in entry.get("link", []):
            if link['@ref'] == "scopus":
                url = link['@href']
        results.append({
            'title': entry.get('dc:title'),
            'url': url,
        })

    return results
