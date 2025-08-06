import instaloader
import csv
import re
import os
import streamlit as st
import yt_dlp
import requests
from bs4 import BeautifulSoup
# import snscrape.modules.twitter as sntwitter
from utils.logger import log_to_browser

def extract_shortcode(url):
    match = re.search(r"/p/([A-Za-z0-9_-]+)", url)
    return match.group(1) if match else None

def fetch_instagram_captions(shortcode, loader):
    try:
        log_to_browser(f"Fetching Instagram caption for {shortcode}")
        post = instaloader.Post.from_shortcode(loader.context, shortcode)
        return post.caption
    except Exception as e:
        print(f"Error fetching caption for {shortcode}: {e}")
        return ""
    
def fetch_youtube_title(shortcode):
    try:
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info_dict = ydl.extract_info(shortcode, download=False)
            log_to_browser(f"Fetching YouTube caption for {shortcode}")
            return info_dict.get('title', 'N/A')
    except Exception as e:
        print(f"Failed to fetch title for {shortcode}: {e}")
        return None

def fetch_reddit_post(url):
    if not url.endswith(".json"):
        url = url.rstrip("/") + ".json"
    headers = {'User-Agent': 'trend-monitor/0.1'}
    try:
        log_to_browser(f"Fetching Reddit post for {url}")
        response = requests.get(url, headers=headers)
        data = response.json()
        post = data[0]['data']['children'][0]['data']
        title = post.get('title', '')
        body = post.get('selftext', '')
        return title, body
    except Exception as e:
        print(f"Error fetching title for Reddit post ({url}): {e}")
        return None, None
    
def fetch_reddit_comment(url):
    if not url.endswith(".json"):
        url = url.rstrip("/") + ".json"
    headers = {'User-Agent': 'trend-monitor/0.1'}
    try: 
        log_to_browser(f"Fetching Reddit comment from {url}")
        response = requests.get(url, headers=headers)
        data = response.json()

        # The comment is in the second object (index 1), under "children"
        comment_data = data[1]['data']['children'][0]['data']
        comment_body = comment_data.get('body', '[no body]')
        author = comment_data.get('author', '[uknown]')
        return comment_body, author
    except Exception as e:
        print(f"Error fetching Reddit comment ({url}): {e}")
        return None, None
    
# def fetch_tweet(url):
#     headers = {'User-Agent': 'Mozilla/5.0'}
#     resp = requests.get(url, headers=headers)
#     soup = BeautifulSoup(resp.text, 'html.parser')
#     print(soup)
#     return soup.title.string

# def fetch_tweet_text(url):
#     tweet_id = url.split("/")[-1]
#     print('tweet id', tweet_id)

def enrich_captions(input_file, output_file):
    log_to_browser(f"Enriching captions from {input_file} to {output_file}")
    # Initialize Instaloader only once
    L = instaloader.Instaloader()

    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Input file not found: {input_file}")

    with open(input_file, newline='', encoding='utf-8') as infile, open(output_file, 'w', newline='', encoding='utf-8') as outfile:
        reader = csv.DictReader(infile)
        # reader_list = list(reader)
        fieldnames = reader.fieldnames + ["caption"] + ["body"]
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()

        # for row in reader:
        #     if row["platform"] == "instagram" and row["url"]:
        #         shortcode = extract_shortcode(row["url"])
        #         if shortcode:
        #             caption = fetch_caption(shortcode, L)
        #             row["caption"] = caption
        #         else:
        #             row["caption"] = ""
        #     else:
        #         row["caption"] = ""
        #     writer.writerow(row)
        # Streamlit progress bar
        # total = len(reader_list)
        # progress = st.progress(0) if st else None

        for i, row in enumerate(reader):
            if row["platform"] == "instagram" and row["url"]:
                shortcode = extract_shortcode(row["url"])
                row["caption"] = fetch_instagram_captions(shortcode, L) if shortcode else ""
            elif row["platform"] == "youtube" and row["url"]:
              row["caption"] = fetch_youtube_title(row["url"])
            elif row["platform"] == "reddit_posts" and row["url"]:
                title, body = fetch_reddit_post(row["url"])
                row["caption"] = title
                row["body"] = body
            elif row["platform"] == "reddit_comments" and row["url"]:
                comment_text, author = fetch_reddit_post(row["url"])
                row["author"] = author
                row["caption"] = comment_text
            # elif row["platform"] == "twitter" and row["url"]:
            #     fetch_tweet_text(row["url"])
            elif row["platform"] == "tiktok" and row["content"]:
                row["caption"] = row["content"]
            else:
                row["caption"] = ""
            writer.writerow(row)

            # if progress:
            #     progress.progress((i + 1) / total)
    
    log_to_browser("Caption enrichment complete!")
    print(f"✅ Captions added. Enriched data saved to {output_file}")

if __name__ == "__main__":
    enrich_captions("output/forumscout_data.csv", "output/forumscout_data_with_captions.csv")
