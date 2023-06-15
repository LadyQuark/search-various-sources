from html import unescape
import logging
import requests
import xmltodict
import pprint
from common import create_json_file, load_existing_json_file
from transform_for_db import transform_rss_item, transform_itunes, transform_spotify, add_spotify_data, scrape_itunes_metadata, add_itunes_data
from urllib.parse import urlparse
import match_spotify
from progress import progress
from ratelimiter import RateLimiter


logger = logging.getLogger('podcast-log')
pp = pprint.PrettyPrinter(depth=6)
attributes = ['titleTerm', 'languageTerm', 'authorTerm', 'genreIndex', 'artistTerm', 'ratingIndex', 'keywordsTerm', 'descriptionTerm']

@RateLimiter(max_calls=20, period=60)
def search_podcasts(search_term, limit=10, search_type="podcastEpisode", attribute=None, offset=0):
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
        "offset": offset
    }
    if attribute:
        payload['attribute'] = attribute
    # payload_str = parse.urlencode(payload, safe=':+')
    url = "https://itunes.apple.com/search"
    try:
        # print(f"Searching podcasts for {search_term}")
        response = requests.get(url, params=payload)
        response.raise_for_status()
    
    except requests.exceptions.ConnectionError as e:
        if e.errno == -2:
            logger.warning("Too many retries")
            raise Exception("Too many retries")
        raise Exception(e)
    
    except requests.exceptions.HTTPError as e:
        if response.status_code == 403:
            print("Quota exceeded for iTunes Search API")
            logger.warning("Quota exceeded for iTunes Search API")
            raise Exception("Quota exceeded for iTunes Search API")
        logger.warning(f"iTunes Search API: Failed search for {search_term}: {e}")
        return []
    
    except Exception as e:
        logger.warning(f"iTunes Search API: Failed search for {search_term}: {e}")
        return []
    
    # Parse response
    try:
        data = response.json()
        results = data['results']
        if not attribute:
            for item in results:
                item['tag'] = search_term
        # results = []
        # for item in data['results']:         
        #     results.append({
        #         'feedUrl': item['feedUrl'] if 'feedUrl' in item else None,
        #         'podcastName': item['collectionName'],
        #         'podcastId': item['collectionId'],
        #         'podcastUrl': item['collectionViewUrl'],
        #         'title': item.get('trackName'),
        #         'url': item.get('trackViewUrl'),
        #         'tag': search_term,
        #         'original': item,
        #     })
    except Exception as e:
        # print(f"Failed parsing {search_term}: {e}")
        logger.warning(f"Failed parsing {search_term}: {e}")
        return results
    
    return results


def get_podcast_from_rss_feed(search_result):
    """ 
    Fetches RSS feed and returns all episodes
    """
    
    # Search if already downloaded RSS feed
    rss_filename = search_result['collectionName'] + " " + str(search_result['collectionId'])
    data_dict = load_existing_json_file(folder="original_rss", name=rss_filename)
    
    if not search_result['feedUrl']:
        logger.warning(f"RSS: No Feed URL for {search_result['collectionName']}")
        return None

    elif not data_dict:
        # print(f"Getting RSS file for {search_result['collectionName']}")
        try:
            response = requests.get(search_result['feedUrl'])
            response.raise_for_status()
        except requests.RequestException:
            # print(f"Unable to fetch RSS for {search_result['collectionName']}")
            logger.warning(f"RSS: Failed fetch for {search_result['collectionName']}")
            return None

        # Parse xml response as dict
        try:
            data_dict = xmltodict.parse(response.content)
        except Exception as e:
            logger.warning(f"RSS: {search_result['collectionName']}: {e}")
            return None
        else:
            data_dict = data_dict["rss"]["channel"]
        
        # Create json file for podcast in folder `original_rss`
        create_json_file(
            folder="original_rss", name=rss_filename, source_dict=data_dict
        )
    
    # Extract info about podcast from header tags
    search_result['authors'] = data_dict.get("itunes:author", data_dict.get("author", ""))
    
    # Check `data_dict['item']`
    if isinstance(data_dict["item"], list):
        items = data_dict["item"]
    elif isinstance(data_dict["item"], dict):
        # print("This isn't a list")
        items = [data_dict["item"]]
    else:
        logger.info(f"Problem with data from {search_result['collectionName']}")
        return None

    return items


def get_episode_from_rss_feed(search_result):
    """ 
    Returns item in RSS feed that matches with episode in search result
    """

    # Get all episodes of the podcast from RSS feed
    items = get_podcast_from_rss_feed(search_result)
    # Loop through each episode item to find the matching episode
    episode = None
    
    if not items:
        return None

    for item in items:
        if match_title(item, search_result['trackName']):
            episode = item
            break

    if not episode:
        logger.warning(f"RSS: Could not find {search_result['trackName']} in {search_result['collectionName']}")
        return None

    # Convert into structured dict
    try:
        db_item = transform_rss_item(episode, search_result)
    except Exception as e:
        # print(f"Transform: Failed for {search_result['collectionName']} - {search_result['trackName']}: {e}")
        logger.warning(f"Transform: Failed for {search_result['collectionName']} - {search_result['trackName']}: {e}")
        return None
    else:
        return db_item
             

def podcast_eps_search_and_transform(search_term, limit=10):

    # 1. Search for term using iTunes Search API
    search_results = search_podcasts(
        search_term=search_term, limit=limit, search_type="podcastEpisode"
        )
    db_items = []
    n = 0
    total = len(search_results)
    
    # 2. For each result transform into database dict
    for i, result in enumerate(search_results):
        progress(i, total, search_term)
            
        podcast_id = result['collectionId']
        itunes_results = itunes_lookup_podcast(podcast_id, limit=1)
        if itunes_results:
            show = next((item for item in itunes_results if item["kind"] == "podcast"), {})
        metadata = scrape_itunes_metadata(podcast_id, show) 
        item = transform_itunes(result, metadata, search_term=result['tag'])
        
        if item:
            # 3. Search in Spotify and add URL
            try:
                spotify_episode = match_spotify.find_spotify_episode(
                    title=item['title'], podcast=item['metadata']['podcast_title']
                    )
            except Exception as e:
                pass
            else:
                if spotify_episode:
                    item = add_spotify_data(item, spotify_episode)
            
            # 4. Collect transformed item
            db_items.append(item)      
    
    return db_items


def match_title(rss_item, episode_title):
    """ 
    Checks variations of titles in a RSS item
    """
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


def itunes_lookup_podcast(podcast_id, limit=200, sort="recent", offset=0):
    """
    Returns all episodes of podcast with ID `podcast_id`
    """

    # Query for podcast info
    payload = {
        "id": podcast_id,
        "media": "podcast",
        "entity": "podcastEpisode",
        "sort": sort,
        "limit": limit,
        "offset": offset
    }
    # payload_str = parse.urlencode(payload, safe='+')
    url = "https://itunes.apple.com/lookup"
    try:
        # print(f"Searching podcasts for {search_term}")
        response = requests.get(url, params=payload)
        response.raise_for_status()
    except requests.RequestException:
        print(f"iTunes Lookup API: Failed for {podcast_id}")
        return []
    
    data = response.json()
    return data['results']


def get_all_episodes_and_transform(show_id):
    """ Fetch all episodes of given podcast and transform"""
    
    # Get recent 200 episodes of podcast with given id using iTunes Lookup API
    results = itunes_lookup_podcast(show_id)
    if not results:
        return None

    # Get metadata
    show = results.pop(0) #first result has show info
    podcast_name = show['collectionName']
    track_count = show['trackCount']
    metadata = scrape_itunes_metadata(show_id, show)     

    # If podcast has more than 200 episodes, get episodes using iTunes Search API 
    if track_count > 200:
        # print("Podcast has more than 200 episodes")
        episode_ids = set([item['trackId'] for item in results])
        for offset in range(0, track_count + 100, 200):
            batch = search_podcasts(
                search_term=podcast_name,
                limit=200,
                search_type="podcastEpisode", 
                attribute="titleTerm",
                offset=offset
            )
            # If result is unique, append to `results`
            for item in batch:
                if str(item['collectionId']) == str(show_id):
                    if item['trackId'] not in episode_ids:
                        results.append(item)
                        episode_ids.add(item['trackId'])
                # else:
                #     print(item['collectionId'], "did not match show ID", show_id)

    # Transform results
    episodes = []
    for item in results:
        episode = transform_itunes(item, metadata)
        if episode:                
            episodes.append(episode)
    
    return episodes
    


def save_all_episodes_podcast_and_transform(query, folder="ki_json", verbose=False, match_fuzzy=True):
    """
    1. Gets ID of each podcast name in `podcast_list`
    2. Gets RSS feed
    3. Gets all episodes using iTunes Lookup API
    4. Matches each RSS item with episodes from iTunes Lookup API
    5. Transform all RSS items + corresponding iTunes link for episode
    6. Saves transformed items in JSON file for each podcast
    """
    
    failed = {}
    if not isinstance(query, str):
        print("Not a valid input")
        return None
    if "podcasts.apple.com" in query:
        parsed_url = urlparse(query)
        split_path = parsed_url.path.rsplit("/", maxsplit=2)
        if len(split_path) != 3 or "id" not in split_path[2]:
            raise Exception("No iTunes ID for podcast found in URL")
        podcast_id = split_path[2].replace("id", "")
    else:
        try:
            results = search_podcasts(search_term=query, limit=5, search_type="podcast")
            if len(results) < 1:
                raise Exception
            elif len(results) > 1:
                if verbose: print(f'\n{query} has more than 1 result')
            podcast = results[0]
            podcast_id = podcast['collectionId']
        except Exception as e:
            if verbose: print(f'Failed to find for {query}: {e}')
            failed[query] = f'Failed to find for {query}: {e}'
            return None

    
    # Transform all episodes
    episodes = get_all_episodes_and_transform(podcast_id)
    if not episodes:
        return None
    podcast_name = episodes[0]['metadata']['podcast_title']

    # Find Spotify show
    spotify_show = match_spotify.find_spotify_show(podcast_name, verbose)
    spotify_show_id = spotify_show.get('id')
    if spotify_show_id:
        spotify_episodes = []
        fuzzy = []
        failed = []
        # Get all episodes of show
        spotify_results = match_spotify.get_show_episodes(spotify_show_id, verbose)
        for batch in spotify_results:
            spotify_episodes.extend(batch)
        # Make dict of unmatched episodes
        spotify_unmatched = {spot['id']: spot for spot in spotify_episodes}

        # Match every iTunes episode with unmatched episodes from Spotify
        for item in episodes:
            episode_title = item["title"]
            matched = False
            item['metadata']['podcast_id']['spotify_id'] = spotify_show_id
            
            for spot_id in spotify_unmatched: 
                spot = spotify_unmatched[spot_id]
                spot_name = spot['name']

                if match_spotify.match_title(episode_title, podcast_name, spot_name):
                    item = add_spotify_data(item, spot, podcast_id=spotify_show_id) 
                    matched = True
                    if verbose: print(f"\n{episode_title} -> {spot_name}")
                    break
            
            if matched:
                if spot_id in spotify_unmatched: del spotify_unmatched[spot_id]
            else:
                failed.append(item)
                # if verbose: print("No matches found!")  
        
        # Match remaining with release date
        if match_fuzzy:
            remaining = []
            for item in failed:
                episode_title = item["title"]
                matched = False
                
                for spot_id in spotify_unmatched: 
                    spot = spotify_unmatched[spot_id]
                    spot_name = spot['name']
                        
                    if item["publishedDate"] == spot["release_date"]:
                        item = add_spotify_data(item, spot, podcast_id=spotify_show_id) 
                        fuzzy.append(item)
                        matched = True
                        if verbose: print(f"\n{episode_title} -> {spot_name}")
                        if verbose: print("Matched by date not title")
                        break
                if matched:
                    if spot_id in spotify_unmatched: del spotify_unmatched[spot_id]
                else:
                    remaining.append(item)
            failed = remaining
                    
        
        # Create JSON files if needed
        if len(fuzzy) > 0:
            create_json_file(folder=folder, name="spotify_fuzzy_matches", source_dict=fuzzy)
            print("Fuzzy matches in Spotify:", len(fuzzy))
        if len(spotify_unmatched) > 0:
            create_json_file(folder=folder, name="spotify_failed", source_dict=spotify_unmatched)
            print("Unmatched episodes in Spotify:", len(spotify_unmatched))
    
    if len(failed) > 0:
        create_json_file(
            folder=folder, name="failed", source_dict=failed)
        print("Unmatched episodes in iTunes:", len(failed))
            
    # Create json file for transformed episodes in folder
    create_json_file(folder=folder, name=podcast_name, source_dict=episodes)
    print("Transformed episodes:", len(episodes))
    

def match_itunes_info(rss_item, itunes_episodes):

    itunes_title = rss_item.get("itunes:title", rss_item.get("title", ""))
    for episode in itunes_episodes:
        if episode['wrapperType'] == "podcastEpisode":
            if episode["trackName"] == itunes_title:
                return {
                    'trackName': itunes_title,
                    'itunes_url': episode['trackViewUrl'],
                    'collectionName': episode['collectionName'],
                    'original': episode,
                    }
            
    return {
            'trackName': itunes_title,
            'itunes_url': None,
            'collectionName': episode['collectionName'],
        }

