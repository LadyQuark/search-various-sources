import datetime
import json
import logging
import pprint
import requests
from bs4 import BeautifulSoup
from common import standard_date, standard_duration, timestamp_ms, clean_html, split_by_and
import traceback
import unicodedata
import re

logger = logging.getLogger('transform')
pp = pprint.PrettyPrinter(depth=6)

ITUNES_THUMBS = ["artworkUrl600", "artworkUrl160", "artworkUrl100", "artworkUrl60"]
BOOK_THUMBS = ["extraLarge", "large", "medium",  "small", "thumbnail", "smallThumbnail"]
YOUTUBE_THUMBS = ["maxres", "standard", "high", "medium", "default"]  

def _db_item(media_type=None, tags=None):
    """ Common fields for KI database item """
    db_item = {
            'title': None,
            'thumbnail': "",
            'description': None,
            'permission': "Global",
            'authors': [],
            'mediaType': media_type,
            'tags': tags,
            'type': "ki",
            'metadata': {
                'transcript': "",
                }, 
            'created': datetime.datetime.utcnow(), 
            'createdBy': None,
            'updated': "",
            'isDeleted': False,
            'original': [],
            'publishedDate': None,
            'status': 1,
            'score': 0,
            'sourceExists': True,
            'slug': ""                    
        }

    return db_item   

def _best_thumbnail(data, choices, key=None):
    if isinstance(data, dict) and data:
        for choice in choices:
            if choice in data and data[choice] != None and data[choice] != "":
                if key:
                    return data[choice][key]
                return data[choice]
    return ""

def transform_rss_item(episode, header, tag=None):
    db_item = _db_item(media_type="audio", tags="podcast")

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

        db_item['title'] = episode.get('itunes:title', episode.get('trackName'))
        db_item['thumbnail'] = thumbnail
        db_item['description'] = clean_html(episode.get('description', ""))
        db_item['authors'] = authors if authors != [""] else [header['collectionName']]
        db_item['metadata']['audio_length'] = duration
        db_item['metadata']['audio_file'] = episode.get('enclosure', {}).get('@url')
        db_item['metadata']['podcast_title'] = header['collectionName']
        db_item['metadata']['url'] = itunes_url if itunes_url else episode.get('link', itunes_result.get('collectionViewUrl'))
        db_item['metadata']['tag'] = tag
        db_item['metadata']['additional_links']['itunes_url'] = itunes_url
        db_item['metadata']['additional_links']['spotify_url'] = None
        db_item['metadata']['transcript'] = episode.get('podcast:transcript', "")
        db_item['original'] = [episode, itunes_result] if itunes_result != {} else [episode]
        db_item['publishedDate'] = standard_date(episode.get('pubDate'))

    except Exception as e:
        print(e.__class__.__name__, e)
        logger.info(f"Failed transform_rss_item: {e.__class__.__name__} {e}")
        return None
    
    return db_item


def transform_itunes(episode, metadata, search_term=None):
    try:
        db_item = _db_item(media_type="audio", tags="podcast")

        authors = metadata['authors'] or episode.get('collectionName', "")
        episode_thumbnail = _best_thumbnail(episode, ITUNES_THUMBS)

        db_item['title'] =  episode.get('trackName')
        db_item['thumbnail'] = metadata['thumbnail'] if metadata['thumbnail'] != "" else episode_thumbnail
        db_item['description'] = clean_html(episode.get('description', ""))
        # db_item['authors'].append(authors)
        db_item['authors'].append(episode.get('collectionName', ""))
        db_item['metadata']['audio_file'] = episode.get('episodeUrl')
        db_item['metadata']['podcast_title'] = episode.get('collectionName')
        db_item['metadata']['url'] = episode.get('trackViewUrl')
        db_item['metadata']['tag'] = [search_term.strip().lower()] if isinstance(search_term, str) else []
        db_item['metadata']['additional_links'] = {
                                                'itunes_url': episode.get('trackViewUrl'),
                                                'spotify_url': None 
                                                }
        db_item['metadata']['podcast_description'] = metadata.get('podcast_description')
        db_item['metadata']['total_episodes'] = metadata.get('total_episodes')
        db_item['metadata']['rating'] = metadata.get('rating')
        db_item['metadata']['rating_count'] = metadata.get('rating_count')
        db_item['metadata']['podcast_id'] = {
                                    'itunes_id': episode.get('collectionId'),
                                    'spotify_id': None
                                    }
        db_item['metadata']['id'] = {
                        'itunes_id': episode.get('trackId'),
                        'spotify_id': None
                        }
        db_item['metadata']['episode_thumbnail'] = episode_thumbnail

        db_item['original'].append(episode)
        db_item['publishedDate'] = standard_date(episode.get('releaseDate'))

        db_item['score'] = calculate_score_podcast(db_item)
        db_item['slug'] = slugify(db_item['title'])
        
    except Exception as e:
        print(e.__class__.__name__, e)
        logger.info(f"Failed transform_itunes: {e.__class__.__name__} {e}")
        return None
    
    return db_item 


def add_spotify_data(db_item, spotify_episode, podcast_id=None):
    # Add Spotify URL
    db_item['metadata']['additional_links']['spotify_url'] = spotify_episode['external_urls']['spotify']
    # Add Spotify ID
    db_item['metadata']['id']['spotify_id'] = spotify_episode.get('id')
    db_item['metadata']['podcast_id']['spotify_id'] = podcast_id or spotify_episode.get('show', {}).get('id')
    # Add Spotify result to original
    db_item['original'].append(spotify_episode)
    # Add description if missing
    if not db_item.get('description') or db_item['description'] == "":
        db_item['description'] = spotify_episode.get('description', "")   
    # Add total_episodes if missing
    if not db_item.get('total_episodes') and "show" in spotify_episode:
        db_item['total_episodes'] = spotify_episode['show']['total_episodes']
    return db_item


def transform_spotify(episode, search_term=None, metadata={}):
    try:
        db_item = _db_item(media_type="audio", tags="podcast")
        show = episode.get('show', metadata)

        db_item['title'] =  episode.get('name')
        db_item['thumbnail'] = show['images'][0]['url']
        db_item['description'] = clean_html(episode.get('description', ""))
        # db_item['authors'].append(show.get('publisher', ""))
        db_item['authors'].append(show.get('name', ""))
        db_item['metadata']['audio_file'] = episode.get('audio_preview_url')
        db_item['metadata']['podcast_title'] = show.get('name')
        db_item['metadata']['url'] = episode['external_urls']['spotify']
        db_item['metadata']['tag'] = [search_term.strip().lower()] if isinstance(search_term, str) else []
        db_item['metadata']['additional_links'] = {
                                    'itunes_url': None,
                                    'spotify_url': episode['external_urls']['spotify'] 
                                    }
        db_item['metadata']['podcast_description'] = clean_html(show.get('description', ""))
        db_item['metadata']['total_episodes'] = show.get('total_episodes')
        db_item['metadata']['rating'] = 0.0
        db_item['metadata']['rating_count'] = 0
        db_item['metadata']['podcast_id'] = {
                    'itunes_id': None,
                    'spotify_id': show.get('id')
                    }                  
        db_item['metadata']['id'] = {
                    'itunes_id': None,
                    'spotify_id': episode.get('id')
                    }
        db_item['metadata']['episode_thumbnail'] = episode['images'][0]['url']
        db_item['original'].append(episode)
        db_item['publishedDate'] = standard_date(episode.get('release_date'))
        db_item['slug'] = slugify(db_item['title'])

    except Exception as e:
        print(e.__class__.__name__, e)
        pp.pprint(episode)
        raise Exception(f"Failed transform_spotify: {e.__class__.__name__} {e}")

    return db_item 


def add_itunes_data(db_item, itunes_episode, metadata=None):
    podcast_id = itunes_episode['collectionId']
    if not metadata:
        metadata = scrape_itunes_metadata(podcast_id)
    db_item['metadata']['additional_links']['itunes_url'] = itunes_episode.get('trackViewUrl')
    db_item['metadata']['rating'] = metadata.get('rating')
    db_item['metadata']['rating_count'] = metadata.get('rating_count')
    db_item['metadata']['podcast_id']['itunes_id'] = podcast_id
    db_item['metadata']['id']['itunes_id'] = itunes_episode.get('trackId')
    db_item['metadata']['audio_file'] = itunes_episode.get('episodeUrl', db_item['metadata']['audio_file'])
    db_item['original'].append(itunes_episode)  
    db_item['score'] = calculate_score_podcast(db_item)          


def transform_book(item, search_term):

    try:
        db_item = _db_item(media_type="books", tags="books")
        volume = item['volumeInfo']

        if not volume.get('description') or volume['description'] == "":
            raise Exception("No description found")     

        authors = [a.strip() for a in volume.get('authors', []) if a.strip() != ""]

        db_item['title'] = volume['title']
        db_item['thumbnail'] = _best_thumbnail(volume.get('imageLinks'), BOOK_THUMBS)
        db_item['description'] = clean_html(volume.get('description', ""))
        db_item['authors'] = authors
        db_item['metadata']['id'] = item['id']
        db_item['metadata']['url'] = volume['previewLink']
        db_item['metadata']['category'] = volume.get('categories', [])
        db_item['metadata']['rating'] = volume.get('averageRating', 0)
        db_item['metadata']['rating_count'] = volume.get('ratingsCount', 0)
        db_item['metadata']['tag'] = [search_term.strip().lower()] if isinstance(search_term, str) else []
        db_item['original'].append(item)
        db_item['publishedDate'] = standard_date(volume.get('publishedDate'))  
        db_item['slug'] = slugify(db_item['title']) 
        
    except Exception as e:
        print(e.__class__.__name__, e)
        logger.info(f"Failed transform_book: {e.__class__.__name__} {e}")
        return None
    
    return db_item


def transform_youtube(item, search_term, type="youtube"):

    try:
        db_item = _db_item(media_type="video", tags="youtube")
        snippet = item['snippet']
        statistics = item.get('statistics', {})

        db_item['title'] = snippet.get('title')
        db_item['thumbnail'] = _best_thumbnail(snippet.get('thumbnails'), YOUTUBE_THUMBS, key="url")
        db_item['description'] = clean_html(snippet.get('description', ""))
        db_item['authors'].append(snippet.get('channelTitle', ""))
        db_item['metadata']['id'] = item['id']
        db_item['metadata']['url'] = f"https://www.youtube.com/watch?v={item['id']}"
        db_item['metadata']['comment_count'] = int(statistics.get('commentCount', 0))
        db_item['metadata']['favorite_count'] = int(statistics.get('favoriteCount', 0))
        db_item['metadata']['like_count'] = int(statistics.get('likeCount', 0))
        db_item['metadata']['view_count'] = int(statistics.get('viewCount', 0))
        db_item['metadata']['tag'] = [search_term.strip().lower()] if isinstance(search_term, str) else []
        db_item['original'].append(item)
        db_item['publishedDate'] = standard_date(snippet.get('publishedAt'))
        db_item['slug'] = slugify(db_item['title']) 

    except Exception as e:
        print(e.__class__.__name__, e)
        logger.info(f"Failed transform_youtube: {e.__class__.__name__} {e}")
        # pp.pprint(item)
        return None
    
    return db_item


def transform_scopus(item, search_term=None):

    try:
        db_item = _db_item(media_type="article", tags="research")

        db_item['title'] = item['dc:title']
        db_item['description'] = None
        db_item['authors'] = [item.get('dc:creator')]
        db_item['metadata']['url'] = next(link['@href'] for link in item.get("link", []) if link['@ref'] == "scopus")
        db_item['metadata']['tag'] = [search_term.strip().lower()] if isinstance(search_term, str) else []
        db_item['metadata']['id'] = item['pii']
        db_item['metadata']['citations'] = ""
        db_item['original'] = [item]
        db_item['publishedDate'] = standard_date(item.get('prism:coverDate'))
    
    except Exception as e:
        print(e.__class__.__name__, e)
        logger.info(f"Failed transform_scopus: {e.__class__.__name__} {e}")
        return None
    
    return db_item


def transform_pubmed(data, search_term=None):
    try:
        db_item = _db_item(media_type="article", tags="research")
        
        medline = data['PubmedArticleSet']['PubmedArticle']['MedlineCitation']
        article = medline['Article']
        abstract_text = article['Abstract']['AbstractText']
        author_list = article['AuthorList']['Author']
        
        # Extract description
        description = ""
        if isinstance(abstract_text, str):
            description = abstract_text
        elif isinstance(abstract_text, dict):
            description = abstract_text.get("#text", "")
        elif isinstance(abstract_text, list):
            description = "\n".join(
                item.get("@Label", " ") + item.get("#text", " ")
                for item in abstract_text
                )
        # Extract all authors
        if isinstance(author_list, dict):
            author_list = [author_list]
        authors = []
        for author in author_list:
            a = author.get("ForeName", "") + " " + author.get("LastName", "")
            a = a.strip()
            if a != "":
                authors.append(a)  
        # Extract PubDate
        date_list = data['PubmedArticleSet']['PubmedArticle']['PubmedData']['History']['PubMedPubDate']
        date_list = date_list if isinstance(date_list, list) else [date_list]
        pub_date_dict = next((item for item in date_list if item['@PubStatus'] == "pubmed"), {})
        pub_date = datetime.date(
            year=int(pub_date_dict['Year']), 
            month=int(pub_date_dict.get('Month', 0)),
            day=int(pub_date_dict.get('Day', 0)),
            ).isoformat()
        # Extract keywords
        keywords = [
            item["#text"] 
            for item in medline.get('KeywordList', {}).get('Keyword', [])
            ]

        db_item['title'] = clean_html(article['ArticleTitle'])
        db_item['description'] = clean_html(description)
        db_item['authors'] = authors
        db_item['metadata']['url'] = "https://pubmed.ncbi.nlm.nih.gov/" + medline['PMID']['#text']
        db_item['metadata']['id'] = int(medline['PMID']['#text'])
        db_item['metadata']['citations'] = ""
        db_item['metadata']['tag'] = [search_term.strip().lower()] if isinstance(search_term, str) else []
        db_item['original'].append(medline)
        db_item['publishedDate'] = pub_date
        db_item['slug'] = slugify(db_item['title']) 

    except Exception as e:
        print(e.__class__.__name__, e)
        logger.info(f"Failed transform_pubmed: {e.__class__.__name__} {e}")
        return None

    return db_item 


def transform_scd(data, search_term=None):
    
    try:  
        db_item = _db_item(media_type="article", tags="research")  
        coredata = data['coredata'] 
        creators = coredata.get('dc:creator', [])
        if isinstance(creators, dict):
            creators = [creators]
        url = next((link['@href'] for link in coredata.get("link", []) 
                    if link['@rel'] == "scidir"), None)

        db_item['title'] = coredata['dc:title']
        description = coredata.get('dc:description', "") or ""
        db_item['description'] = clean_html(description.strip())
        db_item['authors'] = [creator["$"] for creator in creators]
        db_item['metadata']['url'] = url
        db_item['metadata']['id'] = url.split('pii/')[1]
        db_item['metadata']['citations'] = ""
        db_item['metadata']['tag'] = [search_term.strip().lower()] if isinstance(search_term, str) else []
        db_item['original'].append(data)
        db_item['publishedDate'] = standard_date(coredata.get('prism:coverDate'))
        db_item['slug'] = slugify(db_item['title']) 
    
    except Exception as e:
        print(e.__class__.__name__, e)
        traceback.print_exc()
        logger.info(f"Failed transform_scd: {e.__class__.__name__} {e}")
        return None

    return db_item


def transform_tedtalks(data, search_term=None):
    try:
        db_item = _db_item(media_type="video", tags="tedtalks")
        video = data['video'] 
        player = json.loads(video['playerData'])

        external = player.get('external', {})
        youtube_url = "https://www.youtube.com/watch?v=" + external.get('code') if external.get('service') == "YouTube" else None
        tag_string = player.get('targeting', {}).get('tag')
        tag = tag_string.split(",") if tag_string else []
        if isinstance(search_term, str):
            tag.append(search_term.strip().lower())

        db_item['title'] = video['title']
        db_item['thumbnail'] = player.get('thumb', "")
        db_item['description'] = clean_html(video['description'].strip())
        db_item['authors'].append(player.get('speaker', ""))
        db_item['metadata']['id'] = video['id']
        db_item['metadata']['url'] = player.get('canonical', f"https://www.ted.com/talks/{video['slug']}")
        db_item['metadata']['tag'] = [search_term.strip().lower()] if isinstance(search_term, str) else []
        db_item['metadata']['video_length'] = str(datetime.timedelta(seconds=video.get('duration', 0)))
        db_item['metadata']['additional_links'] = {'youtube_url': youtube_url}
        db_item['metadata']['language'] = video.get('language')
        db_item['metadata']['view_count'] = video.get('viewedCount', 0)
        db_item['original'].append(data)
        db_item['publishedDate'] = standard_date(video.get('publishedAt'))
        db_item['slug'] = slugify(db_item['title']) 

    except Exception as e:
        print(e.__class__.__name__, e)
        logger.info(f"Failed transform_tedtalks: {e.__class__.__name__} {e}")
        return None

    return db_item


def scrape_itunes_metadata(podcast_id, show={}):
    # default result
    metadata = {
        'podcast_description': None,
        'rating': 0.0,
        'rating_count': 0,
        'total_episodes': show.get('trackCount'),
        'authors': show.get('artistName'),
        'thumbnail': _best_thumbnail(show, ITUNES_THUMBS)
    }
    # Check podcast_id
    if isinstance(podcast_id, int):
        podcast_id = str(podcast_id)
    elif not isinstance(podcast_id, str): 
        return metadata   
    # Construct URL
    base_url = "https://podcasts.apple.com/us/podcast/id"
    url = base_url + podcast_id
    # Get podcast page
    try:
        response = requests.get(url)
        response.raise_for_status()
    except Exception as e:
        print(e)
        return metadata
    
    soup = BeautifulSoup(response.content, "html.parser")

    # Extract description
    section = soup.find("section", class_="product-hero-desc__section")
    if section:
        metadata['podcast_description'] = section.text.strip()
    # Extract element containing ratings
    rating_elems = soup.find_all("figcaption", class_="we-rating-count star-rating__count")
    for elem in rating_elems:
        ratings = elem.text.split(" • ")
        if len(ratings) == 2 and " Rating" in ratings[1]:
            # Return float value of rating and int value of number of ratings
            try:
                rating = float(ratings[0].strip())
                rating_count_str = ratings[1].replace(" Ratings", "").replace(" Rating", "").strip()
                if "K" in rating_count_str:
                    rating_count_str = rating_count_str.replace("K", "")
                    rating_count = int(float(rating_count_str) * 1000)
                else:
                    rating_count = int(rating_count_str)
            except ValueError as e:
                print(e)
            else:
                metadata['rating'] = rating
                metadata['rating_count'] = rating_count
    
    return metadata


def calculate_score_podcast(db_item, score=0):
    metadata = db_item['metadata']
    
    if metadata['rating'] > 4.5:
        if metadata['rating_count'] >= 2000:
            score += 5
        elif metadata['rating_count'] >= 1000:
            score += 4
        elif metadata['rating_count'] >= 500:
            score += 3
        else:
            score += 2
    
    elif metadata['rating'] > 4.0:
        if metadata['rating_count'] >= 2000:
            score += 4
        elif metadata['rating_count'] >= 1000:
            score += 3
        elif metadata['rating_count'] >= 500:
            score += 2
        else:
            score += 1
        
    elif metadata['rating'] > 3.5:
        if metadata['rating_count'] >= 2000:
            score += 3
        elif metadata['rating_count'] >= 1000:
            score += 2
        elif metadata['rating_count'] >= 500:
            score += 1
        else:
            score += 0

    # Total episodes
    if metadata['total_episodes'] > 500:
        score += 3
    elif metadata['total_episodes'] > 300:
        score += 2
    elif metadata['total_episodes'] > 100:
        score += 1

    pub_date = datetime.datetime.strptime(db_item['publishedDate'], "%Y-%m-%d")
    today = datetime.datetime.today()
    days_since_pub = (today - pub_date).days
    if days_since_pub > 730:
        score += -3
    elif days_since_pub > 365:
        score += -2
    elif days_since_pub > 180:
        score += -1

    db_item['score'] = score

    return score


def slugify(value, allow_unicode=False):
    """
    From Django: https://github.com/django/django/blob/main/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize("NFKC", value)
    else:
        value = (
            unicodedata.normalize("NFKD", value)
            .encode("ascii", "ignore")
            .decode("ascii")
        )
    value = re.sub(r"[^\w\s-]", "", value.lower())
    slug = re.sub(r"[-\s]+", "-", value).strip("-_")    
    return slug