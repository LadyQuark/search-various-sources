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

def transform_rss_item(episode, header, tag=[]):
    PODCAST = {
        'mediaType': "audio",
        'tags': "podcast",
    }
    itunes_result = header['original']
    # Get authors from header if RSS item field is empty
    if episode.get('itunes:author') and episode['itunes:author'].strip() != "":
        authors = split_by_and(episode['itunes:author'].strip())
    else:
        authors = split_by_and(header.get('authors', ""))
    # Get thumbnail from `itunes_result` is RSS item field is empty
    if 'itunes:image' in episode and '@href' in episode['itunes:image']:
        thumbnail = episode['itunes:image']['@href']
    else:
        if 'artworkUrl600' in itunes_result:
            thumbnail = itunes_result['artworkUrl600']
        else:
            thumbnail = itunes_result.get('artworkUrl160', itunes_result.get('artworkUrl60', None))
    
    try:
        db_item = {
            'title': header.get('title'), 
            'thumbnail': thumbnail,
            'description': clean_html(episode.get('description', "")), 
            'permission': DEFAULT_VALUES['permission'], 
            'authors': authors if authors != [""] else None, 
            'mediaType': PODCAST['mediaType'], 
            'tags': PODCAST['tags'], 
            'type': DEFAULT_VALUES['type'], 
            'metadata': {
                'audio_length': standard_duration(episode.get('itunes:duration')),
                'audio_file': episode['enclosure'].get('@url') if 'enclosure' in episode and '@url' in episode['enclosure'] else None,
                'podcast_title': header['podcastName'],
                'url': header['url'],
                'transcript': episode.get('podcast:transcript', DEFAULT_VALUES['transcript']),
                'tag': [header.get('tag').strip().lower()],
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
            'publishedDate': standard_date(episode.get('pubDate'))
        }
    except Exception as e:
        print(e)
        logger.info(f"Episode item: {episode} | Header: {header}")
        raise Exception("Key Error / Type Error")
    
    return db_item

def transform_podcast_result(episode, search_term):
    PODCAST = {
        'mediaType': "audio",
        'tags': "podcast",
    }
    if 'artworkUrl600' in episode:
        thumbnail = episode['artworkUrl600']
    else:
        thumbnail = episode.get('artworkUrl160', episode.get('artworkUrl60', None))

    try:
        db_item = {
            'title': episode.get('trackName'), 
            'thumbnail': thumbnail, 
            'description': clean_html(episode.get('description', "")),
            'permission': DEFAULT_VALUES['permission'], 
            'authors': None, 
            'mediaType': PODCAST['mediaType'], 
            'tags': PODCAST['tags'], 
            'type': DEFAULT_VALUES['type'], 
            'metadata': {
                'audio_length': None,
                'audio_file': episode.get('episodeUrl'),
                'podcast_title': episode.get('collectionName'),
                'url': episode.get('trackViewUrl'),
                'transcript': None,
                'tag': [search_term.strip().lower()]
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
        'mediaType': "text-books",
        'tags': "books",
    }
    volume = book_item['volumeInfo']
    # Choose from available thumbnails
    thumbnail_choices = ["extraLarge", "large", "medium",  "small", "thumbnail", "smallThumbnail"]
    thumbnail = None
    if volume.get('imageLinks'):
        for choice in thumbnail_choices:
            if choice in volume['imageLinks']:
                thumbnail = volume['imageLinks'][choice]
                break
     
    try:
        db_item = {
            'title': volume['title'], 
            'thumbnail': thumbnail,
            'description': volume.get('description'), 
            'permission': DEFAULT_VALUES['permission'], 
            'authors': volume.get('authors'), 
            'mediaType': BOOKS['mediaType'], 
            'tags': BOOKS['tags'], 
            'type': DEFAULT_VALUES['type'], 
            'metadata': {
                'url': book_item['selfLink'],
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


def transform_youtube_item(youtube_item, search_term):
    YOUTUBE = {
        'mediaType': "video",
        'tags': "youtube",
    }
    snippet = youtube_item['snippet']
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
            'title': snippet['title'], 
            'thumbnail': thumbnail,
            'description': snippet.get('description'), 
            'permission': DEFAULT_VALUES['permission'], 
            'authors': snippet.get('channelTitle'), 
            'mediaType': YOUTUBE['mediaType'], 
            'tags': YOUTUBE['tags'], 
            'type': DEFAULT_VALUES['type'], 
            'metadata': {
                'url': f"https://www.youtube.com/watch?v={youtube_item['id']['videoId']}",
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
            'original': [youtube_item], 
            'publishedDate': standard_date(snippet.get('publishedAt')),
        }
    except Exception as e:
        pp = pprint.PrettyPrinter(depth=6)
        pp.pprint(youtube_item)
        raise Exception(e)
    
    return db_item