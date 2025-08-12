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
from pathlib import Path
import praw

# For Instaloader, need to extract shortcode from URL
def extract_shortcode(url):
    match = re.search(r"/p/([A-Za-z0-9_-]+)", url)
    return match.group(1) if match else None

def fetch_instagram_captions(shortcode, loader):
    try:
        # log_to_browser(f"Fetching Instagram caption for {shortcode}")
        post = instaloader.Post.from_shortcode(loader.context, shortcode)
        return post.caption
    except Exception as e:
        print(f"Error fetching caption for {shortcode}: {e}")
        return ""
    
# def fetch_youtube_title(shortcode):
#     try:
#         with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
#             info_dict = ydl.extract_info(shortcode, download=False)
#             # log_to_browser(f"Fetching YouTube caption for {shortcode}")
#             return info_dict.get('title', 'N/A')
#     except Exception as e:
#         print(f"Failed to fetch title for {shortcode}: {e}")
#         return None

# def fetch_youtube_title(shortcode):
#     try:
#         # Optional: Load cookies if available
#         cookies_path = Path("youtube_cookies.txt")
#         ydl_opts = {"quiet": True}

#         if cookies_path.exists():
#             ydl_opts["cookiefile"] = str(cookies_path)
#         else:
#             print("[YouTube] No cookies file found — attempting public access")

#         with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#             info_dict = ydl.extract_info(shortcode, download=False)
#             return info_dict.get("title", "N/A")

#     except yt_dlp.utils.DownloadError as e:
#         # Specific yt-dlp error handling
#         if "Sign in to confirm" in str(e):
#             print(f"[YouTube] Login required for {shortcode} — skipping.")
#         else:
#             print(f"[YouTube] Failed to fetch title for {shortcode}: {e}")
#         return None

#     except Exception as e:
#         # Generic fallback
#         print(f"[YouTube] Unexpected error for {shortcode}: {e}")
#         return None


# Using YouTube API Key
def fetch_youtube_title(video_url: str) -> str | None:
    """Fetch a YouTube video title via YouTube Data API v3."""
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        print("❌ YOUTUBE_API_KEY not set — skipping YouTube title fetch")
        return None

    # Extract video ID from the URL
    match = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", video_url)
    if not match:
        print(f"❌ Invalid YouTube URL: {video_url}")
        return None
    video_id = match.group(1)

    # Call the API
    url = (
        f"https://www.googleapis.com/youtube/v3/videos"
        f"?part=snippet&id={video_id}&key={api_key}"
    )
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        if not items:
            print(f"⚠️ No video found for ID {video_id}")
            return None
        return items[0]["snippet"]["title"]
    except Exception as e:
        print(f"❌ Failed to fetch YouTube title: {e}")
        return None


# def fetch_reddit_post(url):
#     if not url.endswith(".json"):
#         url = url.rstrip("/") + ".json"
#     headers = {'User-Agent': 'trend-monitor/0.1'}
#     try:
#         # log_to_browser(f"Fetching Reddit post for {url}")
#         response = requests.get(url, headers=headers)
#         data = response.json()
#         post = data[0]['data']['children'][0]['data']
#         title = post.get('title', '')
#         body = post.get('selftext', '')
#         return title, body
#     except Exception as e:
#         print(f"Error fetching title for Reddit post ({url}): {e}")
#         return None, None

def make_reddit_client():
    return praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        refresh_token=os.getenv("REDDIT_REFRESH_TOKEN"),
        user_agent="trend-monitor:trend-monitoring:0.1 (by /u/your_reddit_username)",
        ratelimit_seconds=60,
    )

def fetch_reddit_post_api(url: str):
    import re
    def _extract_submission_id(u: str):
        for pat in (r"/comments/([a-z0-9]{5,8})", r"redd\.it/([a-z0-9]{5,8})"):
            m = re.search(pat, u, re.I)
            if m: return m.group(1)
        return None

    sub_id = _extract_submission_id(url)
    if not sub_id:
        print(f"[Reddit API] Could not parse submission id from: {url}")
        return None, None

    reddit = make_reddit_client()
    sub = reddit.submission(id=sub_id)
    # Touch attributes to fetch
    title = sub.title or ""
    body = sub.selftext or ""
    return title, body
    
def fetch_reddit_comment(url):
    if not url.endswith(".json"):
        url = url.rstrip("/") + ".json"
    headers = {'User-Agent': 'trend-monitor/0.1'}
    try: 
        # log_to_browser(f"Fetching Reddit comment from {url}")
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
    print(f"Enriching captions from {input_file} to {output_file}")
    # log_to_browser(f"Enriching captions from {input_file} to {output_file}")

    # Initialize Instaloader only once
    L = instaloader.Instaloader()

    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Input file not found: {input_file}")

    # 🔁 First pass: count total rows
    with open(input_file, newline='', encoding='utf-8') as f:
        total = sum(1 for _ in csv.DictReader(f))

    # Second pass: use total number of rows
    with open(input_file, newline='', encoding='utf-8') as infile, open(output_file, 'w', newline='', encoding='utf-8') as outfile:
        reader = csv.DictReader(infile)
        # reader_list = list(csv.DictReader(infile))
        fieldnames = reader.fieldnames + ["caption"] + ["body"]
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        # rows = list(reader)
        # total = len(rows)

        progress_text = "Scraping captions now. Please be patient."
        progress_bar = st.progress(0, text=progress_text)

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
                comment_text, author = fetch_reddit_comment(row["url"])
                row["author"] = author
                row["caption"] = comment_text
            # elif row["platform"] == "twitter" and row["url"]:
            #     fetch_tweet_text(row["url"])
            elif row["platform"] == "tiktok" and row["content"]:
                row["caption"] = row["content"]
            else:
                row["caption"] = ""
            writer.writerow(row)

            progress_bar.progress((i + 1) / total, text=f"Processing {i+1} of {total}")

        progress_bar.empty()
        # log_to_browser("Caption enrichment complete!")
        print(f"✅ Captions added. Enriched data saved to {output_file}")

if __name__ == "__main__":
    enrich_captions("output/forumscout_data.csv", "output/forumscout_data_with_captions.csv")
