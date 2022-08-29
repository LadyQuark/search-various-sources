from html import unescape
import logging
import requests
import xmltodict

from common import create_json_file, load_existing_json_file
from transform_for_db import transform_podcast_result, transform_rss_item
from urllib import parse

logger = logging.getLogger('podcast-log')

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
        "term": search_term,
        "media": "podcast",
        "entity": search_type,
        "limit": limit,
    }
    payload_str = parse.urlencode(payload, safe=':+')
    url = "https://itunes.apple.com/search"
    try:
        print(f"Searching podcasts for {search_term}")
        response = requests.get(url, params=payload_str)
        response.raise_for_status()
    except requests.RequestException:
        print(f"Failed for {search_term}")
        logger.warning(f"iTunes Search API: Failed search for {search_term}")
        return []
    
    # Parse response
    try:
        data = response.json()
        results = []
        for item in data['results']:         
            results.append({
                'feedUrl': item['feedUrl'] if 'feedUrl' in item else None,
                'podcastName': item['collectionName'],
                'podcastId': item['collectionId'],
                'podcastUrl': item['collectionViewUrl'],
                'title': item['trackName'],
                'url': item['trackViewUrl'],
                'tag': search_term,
                'original': item,
            })
    except Exception as e:
        print(f"Failed parsing {search_term}: {e}")
        logger.warning(f"Failed parsing {search_term}: {e}")
        return results
    
    return results

def get_info_from_rss_feed(search_result):
    # Search if already downloaded RSS feed
    rss_filename = search_result['podcastName'] + " " + str(search_result['podcastId'])
    data_dict = load_existing_json_file(folder="original_rss", name=rss_filename)
    
    if not search_result['feedUrl']:
        logger.warning(f"RSS: No Feed URL for {search_result['podcastName']}")
        return None

    elif not data_dict:
        print(f"Getting RSS file for {search_result['podcastName']}")
        try:
            response = requests.get(search_result['feedUrl'])
            response.raise_for_status()
        except requests.RequestException:
            print(f"Unable to fetch RSS for {search_result['podcastName']}")
            logger.warning(f"RSS: Failed fetch for {search_result['podcastName']}")
            return None

        # Parse xml response as dict
        try:
            data_dict = xmltodict.parse(response.content)
        except Exception as e:
            logger.warning(f"RSS: {search_result['podcastName']}: {e}")
            return None
        else:
            data_dict = data_dict["rss"]["channel"]
        
        # Create json file for podcast in folder `original_rss`
        create_json_file(
            folder="original_rss", name=rss_filename, source_dict=data_dict
        )
    
    # Extract info about podcast from header tags
    search_result['authors'] = data_dict.get("itunes:author", data_dict.get("author", ""))
    # Check type of `data_dict['item']`
    if isinstance(data_dict["item"], list):
        items = data_dict["item"]
    elif isinstance(data_dict["item"], dict):
        print("This isn't a list")
        items = [data_dict["item"]]
    else:
        logger.info(f"Problem with data from {search_result['podcastName']}")
        return None

    # Loop through each dict representing episode in list `items`
    for item in items:
        match = False
        if match_title(item, search_result['title']):
            episode = item
            match = True
            break

    if not match:
        logger.warning(f"RSS: Could not find {search_result['title']} in {search_result['podcastName']}")
        return None
            

    # Convert into structured dict
    try:
        db_item = transform_rss_item(episode, search_result)
    except Exception as e:
        print(f"Transform: Failed for {search_result['podcastName']} - {search_result['title']}: {e}")
        logger.warning(f"Transform: Failed for {search_result['podcastName']} - {search_result['title']}: {e}")
        return None
    else:
        return db_item

def get_info_from_search_result(search_result, search_term):
    try:
        db_item = transform_podcast_result(search_result, search_term)
    except Exception as e:
        print(f"Transform without RSS: Failed for {search_result['podcastName']} - {search_result['title']}: {e}")
        logger.warning(f"Transform without RSS: Failed for {search_result['podcastName']} - {search_result['title']}: {e}")
        return None
    return db_item

def podcast_eps_search_and_transform(search_term, limit=10):
    search_results = search_podcasts(
        search_term=search_term, limit=limit, search_type="podcastEpisode"
        )
    db_items = []
    n = 0
    total = len(search_results)
    # For each result, get info from RSS feed and transform into database dict
    for result in search_results:
        n += 1
        print(f"{n}/{total}")
        item = get_info_from_rss_feed(result)
        if item:
            db_items.append(item)
        else:
            item = get_info_from_search_result(result['original'], result['tag'])
            if item:
                db_items.append(item)
    return db_items

def match_title(rss_item, episode_title):
    if not rss_item:
        return False
    
    itunes_title = rss_item.get('itunes:title')
    title = rss_item.get('title')
    all_titles = []
    
    if isinstance(itunes_title, str):
        itunes_title = itunes_title.strip()
        all_titles.append(itunes_title)
        all_titles.append(unescape(itunes_title))
    
    if isinstance(title, list):
        all_titles.extend([t.strip() for t in title])
    elif isinstance(title, str):
        title = title.strip()
        all_titles.append(unescape(title))
    
    return episode_title.strip() in all_titles