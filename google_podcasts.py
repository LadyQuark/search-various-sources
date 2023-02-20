import requests
from common import *
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote
import pprint

pp = pprint.PrettyPrinter(depth=6)
GOOGLE_PODCAST_BASE_URL = "https://podcasts.google.com/"

def search_google_podcasts(podcast_name):
    podcast_name = podcast_name.strip().strip("/")
    try:
        search_component = quote(podcast_name, safe="")
        url = urljoin(
            base="https://podcasts.google.com/search/",
            url=search_component)
        response = requests.get(url)
        response.raise_for_status()
    except Exception as e:
        raise Exception(f"Failed fetching URL {url}: {e}")

    soup = BeautifulSoup(response.content, "html.parser")

    try:
        results_div = soup.find("div", class_="tD25lb")
        first_result = results_div.find("div")
        podcast_component = first_result.find("a").attrs['href']
        podcast_url = urljoin(GOOGLE_PODCAST_BASE_URL, podcast_component.strip("./"))
        return podcast_url
    except Exception as e:
        print(e.__class__.__name__, e)
        return None

def scrape_google_podcast(url):
    url = remove_queries(url)
    # Get podcast page
    try:
        _, podcast_id = url.rsplit("/feed/", maxsplit=1)
        response = requests.get(url)
        response.raise_for_status()
    except Exception as e:
        raise Exception(f"Failed fetching URL {url}: {e}")
    
    soup = BeautifulSoup(response.content, "html.parser")
    try:
        # Get podcast details
        div_title = soup.find("div", class_="ZfMIwb")
        div_publisher = soup.find("div", class_="BpVHBf")
        if not div_title:
            unavailable = soup.find(text="This podcast is not available or not yet published")
            if unavailable:
                raise Exception(f"Podcast not available on Google: {url}")
            else:
                raise Exception("Scraping error")
        podcast_title = div_title.text.strip()
        publisher = div_publisher.text.strip() if div_publisher else None

        # Get all episodes
        a_episodes = soup.find_all("a", class_="D9uPgd")
        episodes = []
        for item in a_episodes:
            ep_component = remove_queries(item.attrs['href'].strip("./"))
            try:
                _, episode_id = ep_component.rsplit("/episode/", maxsplit=1)
            except ValueError:
                continue
            episode_url = urljoin(GOOGLE_PODCAST_BASE_URL, ep_component)
            episode_name = item.find('div', attrs={'class': 'e3ZUqe'}).text.strip()
            pub_date = item.find('div', attrs={'class': 'OTz6ee'}).text.strip()
            episodes.append({
                "title": episode_name,
                "id": episode_id,
                "google_url": episode_url,
                "publishedDate": standard_date(pub_date),
            })


    except Exception as e:
        raise Exception(f"Scraping Google Podcast failed: {e}")
    
    return { 
            'podcast_title': podcast_title,
            'authors': [publisher],
            "podcast_id": podcast_id,
            "episodes": episodes
            }    


def scrape_google_podcast_episode(url):
    # Get podcast page
    try:
        response = requests.get(url)
        response.raise_for_status()
    except Exception as e:
        raise Exception(f"Failed fetching URL {url}: {e}")
    
    soup = BeautifulSoup(response.content, "html.parser")

    try:
        podcast_path, episode_id = url.rsplit("/episode/", maxsplit=1)
        _, podcast_id = podcast_path.rsplit("/", maxsplit=1)
    except ValueError:
        raise Exception("Google Podcast URL does not point to a episode")

    try:
        div_title = soup.find("div", class_="wv3SK")
        a_podcast = soup.find("a", class_="ik7nMd")
        div_publisher = soup.find("div", class_="J3Ov7d")
        if not div_title or not a_podcast:
            unavailable = soup.find(text="This podcast is not available or not yet published")
            if unavailable:
                raise Exception(f"Podcast not available on Google: {url}")
            else:
                raise Exception("Scraping error")
        title = div_title.text.strip()
        podcast_title = a_podcast.text.strip()
        publisher = publisher.text.strip() if div_publisher else None
    except Exception as e:
        raise Exception(f"Scraping Google Podcast failed: {e}")
    
    return {'title': title, 
            'podcast_title': podcast_title,
            'publisher': publisher,
            "episode_id": episode_id,
            "podcast_id": podcast_id
            }