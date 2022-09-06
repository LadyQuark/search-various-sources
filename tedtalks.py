from videos import search_youtube_channel
from transform_for_db import transform_youtube_item
import logging
from common import load_existing_json_file

logger = logging.getLogger('ted-log')

CHANNEL_TED = "UCAuUUnT6oDeKwE6v1NGQxug"
CHANNEL_TEDED = "UCsooa4yRKGN_zEE8iknghZA"
TED_DB = load_existing_json_file(folder="db", name="ted_db")


def ted_youtube_search_and_transform(search_term, limit=10, include_ted_ed=False):
    # Initialise variables
    search_results = []
    db_items = []
    
    # Search for videos in TED's channels on Youtube
    if include_ted_ed:
        limit = limit // 2
    ted = search_youtube_channel(search_term, CHANNEL_TED, limit)
    search_results.extend(ted)
    if include_ted_ed:
        ted_ed = search_youtube_channel(search_term, CHANNEL_TEDED, limit)
        search_results.extend(ted_ed)
    
    # Transform each result
    for result in search_results:
        try:
            item = transform_youtube_item(result, search_term, type="tedtalks")
            youtube_url = item['metadata']['url']
            ted_item = TED_DB[youtube_url]
            item['title'] = ted_item['title']
            item['description'] = ted_item['description']
            item['authors'] = ted_item['speaker']
            item['metadata']['url'] = ted_item['url']
            item['metadata']['video_length'] = ted_item['length']
            item['publishedDate'] = ted_item['publishdate']
            item['original'].append(ted_item)

        except Exception as e:
            logger.warning(f"Transform error: {e}")
        else:
            db_items.append(item)
    
    return db_items