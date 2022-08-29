from datetime import datetime
from dateutil.parser import parse
from html import unescape
import json
import os
from pathlib import Path
import re

RE_TAG = re.compile('<.*?>')
RE_SPACE_TAG = re.compile('&nbsp;')
RE_EOL_TAG = re.compile('</p>|(<br>)+|(<br/>)+')

def standard_date(pub_date):
    if pub_date:
        try:
            date = parse(pub_date)
            # date = datetime.strptime(pub_date, '%a, %d %b %Y %H:%M:%S %z')
            pub_date = date.strftime("%Y-%m-%d")
        except ValueError:
            return None
    
    return pub_date

def standard_duration(audio_length):
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
    utc_time = datetime.utcnow()
    return int(utc_time.timestamp() * 1000)


def clean_html(raw_html):
    if not isinstance(raw_html, str):
        return raw_html
    
    temp = re.sub(RE_EOL_TAG, '\n', raw_html)
    temp = re.sub(RE_SPACE_TAG, " ", temp)
    temp = re.sub(RE_TAG, '', temp)
    clean_text = unescape(temp)
    return clean_text

def create_json_file(folder, name, source_dict, failed):
    # Convert `data_dict` to JSON formatted string
    json_string = json.dumps(source_dict, indent=4)
    try:
        # Create valid file name
        filename = f"{get_valid_filename(name)}.json"
        # Create folder if does not already exist
        Path(folder).mkdir(parents=True, exist_ok=True)
        # Join folder and filename
        filepath = os.path.join(folder, filename)
    except Exception as e:
        print(e)
        failed[name] = "Could not create valid file name or folder"
        return
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

def load_existing_file(folder, name):
    try:
        # Create valid file name
        filename = f"{get_valid_filename(name)}.json"
        # Join folder and filename
        filepath = os.path.join(folder, filename)
    except Exception as e:
        print(e)
        return None
    else:
        if os.path.isfile(filepath):
            print("File already exists")
            with open(filepath, "r") as f:
                data_dict = json.load(f)
            return data_dict
    return None