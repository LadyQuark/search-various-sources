from videos import search_youtube_channel
from transform_for_db import transform_youtube, transform_tedtalks
import logging
from common import load_existing_json_file
from python_graphql_client import GraphqlClient
import pprint

pp = pprint.PrettyPrinter(depth=6)

logger = logging.getLogger('ted-log')

CHANNEL_TED = "UCAuUUnT6oDeKwE6v1NGQxug"
CHANNEL_TEDED = "UCsooa4yRKGN_zEE8iknghZA"
CHANNEL_TEDX = "UCsT0YIqwnpJCM-mx7-gSA4Q"
TED_DB = load_existing_json_file(folder="db", name="ted_db")


def ted_youtube_search_and_transform(search_term, limit=10, include_tedx=True):
    # Initialise variables
    search_results = []
    db_items = []
    
    # Search for videos in TED's channels on Youtube
    if include_tedx:
        limit = limit // 2
    ted = search_youtube_channel(
        search_term=search_term, 
        channelId=CHANNEL_TED, 
        limit=limit)
    # pp.pprint(ted)
    search_results.extend(ted)
    if include_tedx:
        ted_ed = search_youtube_channel(
            search_term=search_term, 
            channelId=CHANNEL_TEDX, 
            limit=limit)
        search_results.extend(ted_ed)
    # pp.pprint(ted_ed)
    # Transform each result
    for result in search_results:
        try:
            item = transform_youtube(result, search_term, type="tedtalks")
            youtube_url = item['metadata']['url']
            ted_item = TED_DB[youtube_url]
            tedtalk = get_tedtalk(ted_item['url'])
            if tedtalk:
                item = transform_tedtalks(tedtalk, search_term)
            else:
                item['metadata']['url'] = ted_item['url']
                item['title'] = ted_item['title']
                item['description'] = ted_item['description']
                item['authors'] = ted_item['speaker']
                item['metadata']['video_length'] = ted_item['length']
                item['publishedDate'] = ted_item['publishdate']
                item['original'].append(ted_item)

        except Exception as e:
            logger.warning(f"Transform error: {e}")
        else:
            db_items.append(item)
    
    return db_items[:limit]

def get_tedtalk(url):
    talk_id = url.rstrip("/").rsplit("/", maxsplit=1)
    slug = talk_id[-1]
    client = GraphqlClient(endpoint="https://graphql.ted.com/")
    
    # Defined query and variables
    query = """
        query videoQuery($videoslug: String) {
            video(slug:$videoslug) {
                slug
                id
                title
                playerData
                description
                curatorApproved
                audioDownload
                duration
                audioInternalLanguageCode
                hasTranslations
                publishedAt
                videoContext
                recordedOn
                language
                viewedCount
            }
        }
    """
    variables = {"videoslug": slug}

    result = client.execute(query=query, variables=variables)
    data = result.get('data', {})
    if data.get('video'):
        return data
    return None