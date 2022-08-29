from datetime import datetime
from dateutil.parser import parse
from html import unescape
import json
import os
from pathlib import Path
import re
import logging

RE_TAG = re.compile('<.*?>')
RE_SPACE_TAG = re.compile('&nbsp;')
RE_EOL_TAG = re.compile('</p>|(<br>)+|(<br/>)+')
RE_AND = re.compile('\s+&\s+|\s*and\s|\s*,\s*', flags=re.I)

logging.basicConfig(
    filename="log/common.log",
    filemode="a",
    format="%(asctime)s %(name)s %(message)s",
    level=logging.DEBUG)
logger = logging.getLogger('common')

def standard_date(pub_date):
    """ Standardise date format """
    if pub_date:
        try:
            pub_date = pub_date.replace("EDT", "-0400")
            pub_date = pub_date.replace("EST", "-0500")
            pub_date = pub_date.replace("PST", "-0800")
            pub_date = pub_date.replace("PDT", "-0700")
            date = parse(pub_date)
            pub_date = date.strftime("%Y-%m-%d")
        except ValueError:
            logger.warning("Date Problem")
            return None
    
    return pub_date

def standard_duration(audio_length):
    """ Standardise time duration to HH:MM:SS format """
    if audio_length:
        try:
            time = datetime.strptime(audio_length, "%H:%M:%S")
        except ValueError:
            try:
                time = datetime.strptime(audio_length, "%M:%S")
            except ValueError:
                return None

        audio_length = time.strftime("%H:%M:%S")
    
    return audio_length
    
def timestamp_ms():
    """ Get current time in UTC and convert to timestamp in millisecond precision"""
    utc_time = datetime.utcnow()
    return int(utc_time.timestamp() * 1000)


def clean_html(raw_html):
    """
    Cleans HTML text by replacing with end-of-line, spaces and para tags
    with appropriate alternatives. Removes all other HTML tags `<...>`
    Unescapes remaining text.
    """
    if not isinstance(raw_html, str):
        return raw_html
    
    temp = re.sub(RE_EOL_TAG, '\n', raw_html)
    temp = re.sub(RE_SPACE_TAG, " ", temp)
    temp = re.sub(RE_TAG, '', temp)
    clean_text = unescape(temp)
    return clean_text


def split_by_and(input_string):
    if not isinstance(input_string, str):
        logger.info(f"split_by_and: Input is {type(input_string)}")
        return None
    list_of_strings = re.split(RE_AND, input_string)
    return list_of_strings



def create_json_file(folder, name, source_dict):
    # Convert `data_dict` to JSON formatted string
    json_string = json.dumps(source_dict, indent=4)
    
    # Create valid file name and create folder if needed
    try:
        filename = f"{get_valid_filename(name)}.json"
        Path(folder).mkdir(parents=True, exist_ok=True)
        filepath = os.path.join(folder, filename)
    except Exception as e:
        print(e)
        logger.warning(f"Folder: {folder} | Filename: {name} | Error: {e}")
        return None
    
    # Write to JSON file
    with open(filepath, 'w') as file:
            file.write(json_string)

def get_valid_filename(name):
    """
    modified from: https://github.com/django/django/blob/main/django/utils/text.py

    Return the given string converted to a string that can be used for a clean
    filename. Remove leading and trailing spaces; convert other spaces to
    underscores; and remove anything that is not an alphanumeric, dash,
    underscore, or dot.
    >>> get_valid_filename("john's portrait in 2004.jpg")
    'johns_portrait_in_2004.jpg'
    """
    s = str(name).strip().replace(" ", "_")
    s = re.sub(r"(?u)[^-\w.]", "", s)
    if s in {"", ".", ".."}:
        raise Exception("Could not derive file name from '%s'" % name)
    return s


def load_existing_json_file(folder, name):
    # Create standardised file name and join path
    try:
        filename = f"{get_valid_filename(name)}.json"
        filepath = os.path.join(folder, filename)
    except Exception as e:
        print(e)
        return None
    # If json file exists, open and return dictionary
    else:
        if os.path.isfile(filepath):
            with open(filepath, "r") as f:
                data_dict = json.load(f)
            return data_dict
    return None