import instaloader
import csv
import re
import os
import streamlit as st
import yt_dlp
import requests
from bs4 import BeautifulSoup
# import snscrape.modules.twitter as sntwitter
from pathlib import Path
import praw

# For Instaloader, need to extract shortcode from URL
def extract_shortcode(url):
    match = re.search(r"/p/([A-Za-z0-9_-]+)", url)
    return match.group(1) if match else None

def fetch_instagram_captions(shortcode):
    L = instaloader.Instaloader()
    try:
        # log_to_browser(f"Fetching Instagram caption for {shortcode}")
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        return post.caption
    except Exception as e:
        print(f"Error fetching caption for {shortcode}: {e}")
        return ""

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

def enrich_captions(input_file, output_file, st=None):
    # allow headless mode (no Streamlit UI in CI)
    class _NullSt:
        def __getattr__(self, _): return lambda *a, **k: None
    st = st or _NullSt()

    with open(input_file, newline='', encoding='utf-8') as infile, \
         open(output_file, 'w', newline='', encoding='utf-8') as outfile:

        reader = csv.DictReader(infile)

        # Ensure 'caption' and 'body' appear exactly once in header
        base_fields = reader.fieldnames or []
        fieldnames = list(dict.fromkeys(base_fields + ['caption', 'body']))

        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()

        rows = list(reader)

        for i, row in enumerate(rows, start=1):
            # Normalize platform safely
            platform = (row.get("platform") or "").strip().lower()
            url = (row.get("url") or "").strip()

            try:
                if platform == "instagram" and url:
                    shortcode = extract_shortcode(url)
                    row["caption"] = fetch_instagram_captions(shortcode) if shortcode else ""

                elif platform == "youtube" and url:
                    # Prefer API-based fetch in CI to avoid cookies hassle
                    row["caption"] = fetch_youtube_title(url) or ""

                elif platform == "reddit_posts":
                    # ForumScout gives reddit post text in 'snippet' or you already stored it in 'content'
                    row["caption"] = (row.get("content") or row.get("snippet") or "").strip()
                    # If you also want to keep a separate body column, set it too:
                    row["body"] = row.get("body", "") or ""  # or fill with something else if you fetch full text

                elif platform == "reddit_comments" and url:
                    # comment_text, author = fetch_reddit_comment(url)
                    # if author:
                    #     row["author"] = author
                    # row["caption"] = (comment_text or "").strip()
                    row["caption"] = (row.get("content") or row.get("snippet") or "").strip()

                elif platform == "tiktok":
                    # Your TikTok pipeline already stores the caption/description in 'content'
                    row["caption"] = (row.get("content") or "").strip()
                
                elif row["platform"] == "twitter" and row["url"]:
                    row["caption"] = row["content"]
                    
                else:
                    row["caption"] = row.get("caption", "") or ""

            except Exception as e:
                # Don’t fail the whole export on a single row
                print(f"[enrich_captions] Error on platform={platform} url={url}: {e}")
                row["caption"] = row.get("caption", "") or ""
                # keep body if present; otherwise empty
                row["body"] = row.get("body", "") or ""

            # Ensure all expected fields exist before writing (DictWriter drops unknown keys)
            for f in fieldnames:
                row.setdefault(f, "")

            writer.writerow(row)

if __name__ == "__main__":
    enrich_captions("output/forumscout_data.csv", "output/forumscout_data_with_captions.csv")
