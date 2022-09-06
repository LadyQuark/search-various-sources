import requests
import os
from dotenv import load_dotenv, find_dotenv

# Get API key from .env
load_dotenv(find_dotenv())
API_KEY = os.getenv('RAPIDAPI_KEY')

def search_ted(search_term, limit=10):
    """ 
    Searches TED for given search term using API from RapidAPI 
    https://rapidapi.com/Yakup7/api/ted-talk-api/ 
    and outputs list of title and url, default count of 10
    """
    
    # Construct URL
    url = "https://ted-talk-api.p.rapidapi.com/talks"
    payload = {
        "keyword": search_term,
    }
    headers = {
        "X-RapidAPI-Key": API_KEY,
        "X-RapidAPI-Host": "ted-talk-api.p.rapidapi.com"
    }
    payload_str = parse.urlencode(payload, quote_via=parse.quote)
    # Get Response
    try:
        response = requests.get(url, headers=headers, params=payload_str)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Unable to search Ted for {search_term}: {e}")
        return []
    # Parse response
    data = response.json()
    results = [item for item in data]
    print(f"Results: {len(results)}")
    print(response.url)

    return results[:limit]