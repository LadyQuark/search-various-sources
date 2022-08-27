import requests

def search_podcasts(search_term, limit=10, search_type="podcastEpisode"):
    """ 
    Searches podcasts for given search term using iTunes Search API
    https://developer.apple.com/library/archive/documentation/AudioVideo/Conceptual/iTuneSearchAPI/Searching.html#//apple_ref/doc/uid/TP40017632-CH5-SW1
    and outputs list (default count of 10) of `title`, `url`, `feedUrl` (for RSS),
    `trackName`, `trackUrl` are relevant if searching by episode instead of entire podcast
    """

    if search_type not in ["podcast", "podcastEpisode"]:
        print("Invalid search type")
        return None
    
    # Query for podcast info
    payload = {
        "term": requests.utils.quote(search_term),
        "media": "podcast",
        "entity": search_type,
        "limit": limit,
    }
    url = "https://itunes.apple.com/search"
    try:
        response = requests.get(url, params=payload)
        response.raise_for_status()
    except requests.RequestException:
        print(f"Failed for {search_term}")
        return []
    
    # Parse response
    try:
        data = response.json()
        results = []
        for item in data['results']:
            
            results.append({
                'feedUrl': item['feedUrl'] if 'feedUrl' in item else None,
                'podcastName': item['collectionName'],
                'podcastUrl': item['collectionViewUrl'],
                'title': item['trackName'],
                'url': item['trackViewUrl'],
            })
    except Exception as e:
        print(f"Failed parsing {search_term}: {e}")
        return results
    
    return results
