import requests

def search_podcasts(search_term, limit=10, search_type="podcast"):
    if search_type not in ["podcast", "podcastEpisode"]:
        print("Invalid search type")
        return None
    
    # Query for podcast info using iTunes Search API
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
        return None
    
    # Parse response
    try:
        data = response.json()
        results = data['results']
        podcast_list = []
        for item in results:
            # Add RSS feed URL to list `podcast_feeds`
            podcast_list.append({
                'feedUrl': item['feedUrl'] if 'feedUrl' in item else None,
                'title': item['collectionName'],
                'url': item['collectionViewUrl'],
                'trackName': item['trackName'],
                'trackUrl': item['trackViewUrl'],
            })

    except Exception as e:
        # If parsing fails, log & move to next podcast name
        print(f"Failed parsing {search_term}")
        print(e)
        # print(data)
        return podcast_list
    
    return podcast_list
