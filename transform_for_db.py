from common import standard_date, standard_duration, timestamp_ms, clean_html, split_by_and
import logging
import pprint

logger = logging.getLogger('transform')

DEFAULT_VALUES = {
    'thumbnail': None,
    'permission': "Global",
    'type': "ki",
    'transcript': "",
    'createdBy': None,
    'updated': "",
    'isDeleted': False,
}

def transform_rss_item(episode, header, tag=None):
    PODCAST = {
        'mediaType': "audio",
        'tags': "podcast",
    }
    itunes_result = header.get('original', {})
    
    # Check if description is available
    if not episode.get('description') or episode['description'] == "":
        raise Exception("No description found")  
    # Get authors from header if RSS item field is empty
    if episode.get('itunes:author') and episode['itunes:author'].strip() != "":
        authors = split_by_and(episode['itunes:author'].strip())
    else:
        authors = split_by_and(header.get('authors', ""))
    
    # Get thumbnail from `itunes_result` is RSS item field is empty
    thumbnail = None
    if 'itunes:image' in episode and '@href' in episode['itunes:image']:
        thumbnail = episode['itunes:image']['@href']
    else:            
        for choice in ["artworkUrl600", "artworkUrl160", "artworkUrl60"]:
            if choice in itunes_result and itunes_result[choice] != None and itunes_result[choice] != "":
                thumbnail = itunes_result[choice]
                break        
    duration = standard_duration(episode.get('itunes:duration'))
    if not duration:
        duration = standard_duration(itunes_result.get('trackTimeMillis'))
    if tag:
        tag = [tag.strip().lower()]
    elif "tag" in header:
        tag = [header.get('tag').strip().lower()]
    else:
        tag = []

    if 'itunes_url' in header:
        itunes_url = header['itunes_url']
    elif itunes_result and 'trackViewUrl' in itunes_result:
        itunes_url = itunes_result['trackViewUrl']
    else:
        itunes_url = None

    try:
        db_item = {
            'title': episode.get('itunes:title', episode.get('title')), 
            'thumbnail': thumbnail,
            'description': clean_html(episode.get('description', "")), 
            'permission': DEFAULT_VALUES['permission'], 
            'authors': authors if authors != [""] else header['podcastName'], 
            'mediaType': PODCAST['mediaType'], 
            'tags': PODCAST['tags'], 
            'type': DEFAULT_VALUES['type'], 
            'metadata': {
                'audio_length': duration,
                'audio_file': episode['enclosure'].get('@url') if 'enclosure' in episode and '@url' in episode['enclosure'] else None,
                'podcast_title': header['podcastName'],
                'url': itunes_url if itunes_url else episode.get('link', itunes_result.get('collectionViewUrl')),
                'transcript': episode.get('podcast:transcript', DEFAULT_VALUES['transcript']),
                'tag': tag,
                'additional_links': {
                        'itunes_url': itunes_url,
                        'spotify_url': None 
                    }
                }, 
            'created': {
                '$date': {
                    '$numberLong': str(timestamp_ms())
                    }
                }, 
            'createdBy': DEFAULT_VALUES['createdBy'],
            'updated': DEFAULT_VALUES['updated'],
            'isDeleted': DEFAULT_VALUES['isDeleted'],
            'original': [episode, itunes_result] if itunes_result != {} else [episode], 
            'publishedDate': standard_date(episode.get('pubDate'))
        }
    except Exception as e:
        logger.warning(f"Episode item: {episode} | Header: {header}")
        raise Exception(f"Key Error / Type Error: {e}")
    
    return db_item

def transform_podcast_result(episode, search_term=None):
    PODCAST = {
        'mediaType': "audio",
        'tags': "podcast",
    }
    # Check if description is available
    if not episode.get('description') or episode['description'] == "":
        raise Exception("No description found")  
    # Get thumbnail
    thumbnail = None
    for choice in ["artworkUrl600", "artworkUrl160", "artworkUrl60"]:
        if choice in episode and episode[choice] != None and episode[choice] != "":
            thumbnail = episode[choice]
            break
    
    try:
        db_item = {
            'title': episode.get('trackName'), 
            'thumbnail': thumbnail, 
            'description': clean_html(episode['description']),
            'permission': DEFAULT_VALUES['permission'], 
            'authors': [episode.get('collectionName')], 
            'mediaType': PODCAST['mediaType'], 
            'tags': PODCAST['tags'], 
            'type': DEFAULT_VALUES['type'], 
            'metadata': {
                'audio_length': standard_duration(episode.get('trackTimeMillis')),
                'audio_file': episode.get('episodeUrl'),
                'podcast_title': episode.get('collectionName'),
                'url': episode.get('trackViewUrl'),
                'transcript': None,
                'tag': [search_term.strip().lower()] if isinstance(search_term, str) else [],
                'additional_links': {
                        'itunes_url': episode.get('trackViewUrl'),
                        'spotify_url': None 
                    }
                }, 
            'created': {
                '$date': {
                    '$numberLong': str(timestamp_ms())
                    }
                }, 
            'createdBy': DEFAULT_VALUES['createdBy'],
            'updated': DEFAULT_VALUES['updated'],
            'isDeleted': DEFAULT_VALUES['isDeleted'],
            'original': [episode], 
            'publishedDate': standard_date(episode.get('releaseDate'))
        }
    except Exception as e:
        print(e)
        logger.info(f"Episode item: {episode}")
        raise Exception("Key Error / Type Error")

    return db_item


def transform_book_item(book_item, search_term):
    BOOKS = {
        'mediaType': "books",
        'tags': "books",
    }
    volume = book_item['volumeInfo']
    # Check if description is available
    if not volume.get('description') or volume['description'] == "":
        raise Exception("No description found")     
    # Choose from available thumbnails
    thumbnail_choices = ["extraLarge", "large", "medium",  "small", "thumbnail", "smallThumbnail"]
    thumbnail = None
    if volume.get('imageLinks'):
        for choice in thumbnail_choices:
            if choice in volume['imageLinks']:
                thumbnail = volume['imageLinks'][choice]
                break
    
    authors = [a.strip() for a in volume.get('authors', []) if a.strip() != ""]
     
    try:
        db_item = {
            'title': volume['title'], 
            'thumbnail': thumbnail,
            'description': volume.get('description'), 
            'permission': DEFAULT_VALUES['permission'], 
            'authors': authors, 
            'mediaType': BOOKS['mediaType'], 
            'tags': BOOKS['tags'], 
            'type': DEFAULT_VALUES['type'], 
            'metadata': {
                'url': volume['previewLink'],
                'tag': [search_term.strip().lower()],
                }, 
            'created': {
                '$date': {
                    '$numberLong': str(timestamp_ms())
                    }
                }, 
            'createdBy': DEFAULT_VALUES['createdBy'],
            'updated': DEFAULT_VALUES['updated'],
            'isDeleted': DEFAULT_VALUES['isDeleted'],
            'original': [book_item], 
            'publishedDate': standard_date(volume.get('publishedDate')),
        }
    except Exception as e:
        pp = pprint.PrettyPrinter(depth=6)
        pp.pprint(book_item)
        raise Exception(e)
    
    return db_item


def transform_youtube_item(youtube_item, search_term, type="youtube"):
    YOUTUBE = {
        'mediaType': "video",
        'tags': type,
    }
    snippet = youtube_item['snippet']
    # Check if description is available
    if not snippet.get('description') or snippet['description'] == "":
        raise Exception("No description found")     
    # Choose from available thumbnails
    thumbnail_choices = ["high", "medium", "default"]
    thumbnail = None
    if snippet.get('thumbnails'):
        for choice in thumbnail_choices:
            if choice in snippet['thumbnails']:
                thumbnail = snippet['thumbnails'][choice]['url']
                break
     
    try:
        db_item = {
            'title': snippet.get('title'), 
            'thumbnail': thumbnail,
            'description': clean_html(snippet.get('description', "")), 
            'permission': DEFAULT_VALUES['permission'], 
            'authors': snippet.get('channelTitle'), 
            'mediaType': YOUTUBE['mediaType'], 
            'tags': YOUTUBE['tags'], 
            'type': DEFAULT_VALUES['type'], 
            'metadata': {
                'url': f"https://www.youtube.com/watch?v={youtube_item['id']['videoId']}",
                'tag': [search_term.strip().lower()] if search_term else [],
                }, 
            'created': {
                '$date': {
                    '$numberLong': str(timestamp_ms())
                    }
                }, 
            'createdBy': DEFAULT_VALUES['createdBy'],
            'updated': DEFAULT_VALUES['updated'],
            'isDeleted': DEFAULT_VALUES['isDeleted'],
            'original': [youtube_item], 
            'publishedDate': standard_date(snippet.get('publishedAt')),
        }
    except Exception as e:
        print(e)
        raise Exception(e)
    
    return db_item


def transform_scopus_item(scopus_item, search_term):
    RESEARCH = {
        'mediaType': "article",
        'tags': "research",
    }
    for link in scopus_item.get("link", []):
        if link['@ref'] == "scopus":
            url = link['@href']

     
    try:
        db_item = {
            'title': scopus_item['dc:title'], 
            'thumbnail': None, #TODO
            'description': None, #TODO
            'permission': DEFAULT_VALUES['permission'], 
            'authors': scopus_item.get('dc:creator'), 
            'mediaType': RESEARCH['mediaType'], 
            'tags': RESEARCH['tags'], 
            'type': DEFAULT_VALUES['type'], 
            'metadata': {
                'url': url,
                'tag': [search_term.strip().lower()],
                }, 
            'created': {
                '$date': {
                    '$numberLong': str(timestamp_ms())
                    }
                }, 
            'createdBy': DEFAULT_VALUES['createdBy'],
            'updated': DEFAULT_VALUES['updated'],
            'isDeleted': DEFAULT_VALUES['isDeleted'],
            'original': [scopus_item], 
            'publishedDate': standard_date(scopus_item.get('prism:coverDate')),
        }
    except Exception as e:
        raise Exception(e)
    
    return db_item