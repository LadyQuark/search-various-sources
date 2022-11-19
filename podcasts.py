from html import unescape
import logging
import requests
import xmltodict
import pprint
from common import create_json_file, load_existing_json_file
from transform_for_db import transform_rss_item, transform_itunes, add_spotify_data, scrape_itunes_metadata
import match_spotify
from progress import progress


logger = logging.getLogger('podcast-log')
pp = pprint.PrettyPrinter(depth=6)
attributes = ['titleTerm', 'languageTerm', 'authorTerm', 'genreIndex', 'artistTerm', 'ratingIndex', 'keywordsTerm', 'descriptionTerm']

def search_podcasts(search_term, limit=10, search_type="podcastEpisode", attribute=None):
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
    if attribute:
        if attribute in attributes:
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
        results = []
        for item in data['results']:         
            results.append({
                'feedUrl': item['feedUrl'] if 'feedUrl' in item else None,
                'podcastName': item['collectionName'],
                'podcastId': item['collectionId'],
                'podcastUrl': item['collectionViewUrl'],
                'title': item.get('trackName'),
                'url': item.get('trackViewUrl'),
                'tag': search_term,
                'original': item,
            })
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
    rss_filename = search_result['podcastName'] + " " + str(search_result['podcastId'])
    data_dict = load_existing_json_file(folder="original_rss", name=rss_filename)
    
    if not search_result['feedUrl']:
        logger.warning(f"RSS: No Feed URL for {search_result['podcastName']}")
        return None

    elif not data_dict:
        # print(f"Getting RSS file for {search_result['podcastName']}")
        try:
            response = requests.get(search_result['feedUrl'])
            response.raise_for_status()
        except requests.RequestException:
            # print(f"Unable to fetch RSS for {search_result['podcastName']}")
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
    
    # Check `data_dict['item']`
    if isinstance(data_dict["item"], list):
        items = data_dict["item"]
    elif isinstance(data_dict["item"], dict):
        # print("This isn't a list")
        items = [data_dict["item"]]
    else:
        logger.info(f"Problem with data from {search_result['podcastName']}")
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
        if match_title(item, search_result['title']):
            episode = item
            break

    if not episode:
        logger.warning(f"RSS: Could not find {search_result['title']} in {search_result['podcastName']}")
        return None

    # Convert into structured dict
    try:
        db_item = transform_rss_item(episode, search_result)
    except Exception as e:
        # print(f"Transform: Failed for {search_result['podcastName']} - {search_result['title']}: {e}")
        logger.warning(f"Transform: Failed for {search_result['podcastName']} - {search_result['title']}: {e}")
        return None
    else:
        return db_item
             

def get_info_from_search_result(search_result, search_term):
    try:
        db_item = transform_podcast_result(search_result, search_term)
    except Exception as e:
        # print(f"Transform without RSS: Failed for {search_result['collectionName']} - {search_result['trackName']}: {e}")
        logger.warning(f"Transform without RSS: Failed for {search_result['collectionName']} - {search_result['trackName']}: {e}")
        return None
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
            
        podcast_id = result['original']['collectionId']
        itunes_results = itunes_lookup_podcast(podcast_id, limit=1)
        if itunes_results:
            show = next((item for item in itunes_results if item["kind"] == "podcast"), {})
        metadata = scrape_itunes_metadata(podcast_id, show) 
        item = transform_itunes(result['original'], metadata, search_term=result['tag'])
        
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


def itunes_lookup_podcast(podcastId, limit=200, sort="recent", offset=0):
    """
    Returns all episodes of podcast with ID `podcastId`
    """

    # Query for podcast info
    payload = {
        "id": podcastId,
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
        print(f"iTunes Lookup API: Failed for {podcastId}")
        return []
    
    data = response.json()
    return data['results']


def save_all_episodes_podcast_and_transform(podcast_list, folder="ki_json", verbose=False):
    """
    1. Gets ID of each podcast name in `podcast_list`
    2. Gets RSS feed
    3. Gets all episodes using iTunes Lookup API
    4. Matches each RSS item with episodes from iTunes Lookup API
    5. Transform all RSS items + corresponding iTunes link for episode
    6. Saves transformed items in JSON file for each podcast
    """
    
    failed = {}
    total = len(podcast_list)
    for i, name in enumerate(podcast_list):
        # progress(i, total, name)
        
        if isinstance(name, str):
            # Search for podcast names
            try:
                results = search_podcasts(search_term=name, limit=5, search_type="podcast")
                if len(results) < 1:
                    raise Exception
                elif len(results) > 1:
                    if verbose: print(f'\n{name} has more than 1 result')
                podcast = results[0]
            except Exception as e:
                if verbose: print(f'Failed to find for {name}: {e}')
                failed[name] = f'Failed to find for {name}: {e}'
                continue
        elif isinstance(name, int):
            podcast = {}
            podcast['podcastId'] = name
        else:
            return
        
        # Transform all episodes
        episodes = []
        itunes_episodes = itunes_lookup_podcast(podcast['podcastId'])
        show = next((item for item in itunes_episodes if item["kind"] == "podcast"), {})
        metadata = scrape_itunes_metadata(podcast['podcastId'], show) 
        # create_json_file(folder="test", name=name, source_dict=itunes_episodes)
        for item in itunes_episodes:
            if item["wrapperType"] != "podcastEpisode":
                continue
            episode = transform_itunes(item, metadata)
            if episode:                
                episodes.append(episode)

        # Find Spotify show
        podcast_name = show['collectionName']
        spotify_show = match_spotify.find_spotify_show(podcast_name, verbose)
        spotify_show_id = spotify_show['id']
        if spotify_show_id:
            spotify_episodes = []
            fuzzy = []
            failed = []
            # Get all episodes of show
            spotify_results = match_spotify.get_show_episodes(spotify_show_id, verbose)
            for episode_set in spotify_results:
                spotify_episodes.extend(episode_set)

            for item in episodes:
                episode_title = item["title"]
                count_matched = 0
                item['metadata']['podcast_id']['spotify_id'] = spotify_show_id
                
                for spot in spotify_episodes: 
                    if match_spotify.match_title(episode_title, podcast_name, spot['name']):
                        # Update spotify link                
                        item = add_spotify_data(item, spot) 
                        matched = True
                        count_matched += 1
                        if verbose: print(f"\n{episode_title} -> {spot['name']}")
                        break
                    
                    elif item["publishedDate"] == spot["release_date"]:
                        item = add_spotify_data(item, spot) 
                        fuzzy.append(item)
                        matched = True
                        count_matched += 1
                        if verbose: print(f"\n{episode_title} -> {spot['name']}")
                        if verbose: print("Matched by date not title")
                        break
                
                    if not matched:
                        failed.append(item)
                        if verbose: print("No matches found!")  
            
            create_json_file(folder=folder, name="spotify_failed", source_dict=failed)
            create_json_file(folder=folder, name="spotify_fuzzy_matches", source_dict=fuzzy)



        """ 
        # Get all episodes from RSS feed
        rss = get_podcast_from_rss_feed(podcast)            

        else:
            # Matches with 
            itunes_episodes = itunes_lookup_podcast(podcast['podcastId'])
            total_rss = len(rss)
            count_matched = 0
            for item in rss:
                # Set header to the matching episode details from iTunes 
                if itunes_episodes:
                    header = match_itunes_info(item, itunes_episodes)
                    if header['itunes_url']:
                        count_matched += 1
                # if no match is found, set podcast search result as header
                else:
                    header = podcast
                
                # Transform item given info available
                try:
                    episode = transform_rss_item(item, header, tag=None)
                except Exception as e:
                    logger.warning(f"Transform: Failed for {podcast['podcastName']} - {podcast['title']}: {e}")
                    continue
                
                episodes.append(episode)

            print(f"\nMatched {count_matched} out of {total_rss} episodes")

            if count_matched < total_rss:
                pass 
        """
        
        
        # Create json file for transformed episodes in folder
        create_json_file(folder=folder, name=name, source_dict=episodes)
            

    if len(failed) > 0:
        create_json_file(
            folder=folder, name="failed", source_dict=failed)
    

def match_itunes_info(rss_item, itunes_episodes):

    itunes_title = rss_item.get("itunes:title", rss_item.get("title", ""))
    for episode in itunes_episodes:
        if episode['wrapperType'] == "podcastEpisode":
            if episode["trackName"] == itunes_title:
                return {
                    'title': itunes_title,
                    'itunes_url': episode['trackViewUrl'],
                    'podcastName': episode['collectionName'],
                    'original': episode,
                    }
            
    return {
            'title': itunes_title,
            'itunes_url': None,
            'podcastName': episode['collectionName'],
        }

