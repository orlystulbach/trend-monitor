# forumscout_ingestion/main.py
# First run "source ~/.bashrc" in terminal
import os
import requests
import time
import csv
import datetime
from dotenv import load_dotenv
from config import message_queue
from utils.logger import log_to_browser

# Load environment variables
load_dotenv()

# Base API setup
FORUMSCOUT_API_KEY = os.getenv("FORUMSCOUT_API_KEY")  # Replace with your real API key
BASE_URL = "https://forumscout.app/api"

# Keywords and endpoints to track
# Endpoints found here: https://forumscout.app/developers 
KEYWORDS = ["zionism"]

ENDPOINTS = {
    "twitter": "x_search",
    # "reddit_posts": "reddit_posts_search",
    # "reddit_comments": "reddit_comments_search",
    # "youtube": "youtube_search",
    # "linkedin": "linkedin_search",
    # "youtube" "youtube_search"
    # "instagram": "instagram_search"
    # Add more as supported
}

OUTPUT_FILE = "output/forumscout_data.csv"

def fetch_forumscout_data(endpoint, keyword):
    url = f"{BASE_URL}/{endpoint}"
    headers = {
        "X-API-Key": FORUMSCOUT_API_KEY
    }
    params = {
        "keyword": keyword,
        # "sort_by": recent
    }
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching {keyword} from {endpoint}: {response.status_code}")
        return []


def normalize_result(post, platform, keyword):
    return {
        "platform": platform,
        "keyword": keyword,
        "content": post.get("text") or post.get("content") or "",
        "author": post.get("username") or post.get("author") or "",
        "timestamp": post.get("date") or post.get("published_at") or datetime.utcnow().isoformat(),
        "url": post.get("url") or post.get("link") or ""
    }


def write_to_csv(records, output_file):
    if not records:
        print("No records to write.")
        return

    keys = records[0].keys()
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        if f.tell() == 0:
            writer.writeheader()
        writer.writerows(records)

def run_ingestion(keywords, endpoints, output_file="output/forumscout_data.csv"):
    all_records = []

    for platform, endpoint in endpoints.items():
        for keyword in keywords:
            print(f"🔎 Fetching '{keyword}' from {platform}...")
            log_to_browser(f"🔎 Fetching '{keyword}' from {platform}...")
            posts = fetch_forumscout_data(endpoint, keyword)
            normalized = [normalize_result(p, platform, keyword) for p in posts]
            all_records.extend(normalized)
            time.sleep(1)  # avoid rate limits

    write_to_csv(all_records, output_file)
    print(f"✅ Ingested {len(all_records)} records into {output_file}.")


# def run_ingestion():
#     all_records = []
#     for platform, endpoint in ENDPOINTS.items():
#         for keyword in KEYWORDS:
#             print(f"Fetching {keyword} from {platform}...")
#             posts = fetch_forumscout_data(endpoint, keyword)
#             normalized = [normalize_result(p, platform, keyword) for p in posts]
#             all_records.extend(normalized)
#             time.sleep(1)  # Rate limit spacing

#     write_to_csv(all_records)
#     print(f"Ingested {len(all_records)} records.")


if __name__ == "__main__":
    import os
    os.makedirs("output", exist_ok=True)
    run_ingestion(KEYWORDS, ENDPOINTS)
