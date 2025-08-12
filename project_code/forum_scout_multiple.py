# forumscout_ingestion/main.py
# First run "source ~/.bashrc" in terminal
import os
import requests
import time
import csv
import datetime
from dotenv import load_dotenv
from utils.logger import log_to_browser
from project_code.fetch_tiktok_data import scrape_tiktok_data
import pandas as pd

# Load environment variables
load_dotenv()

# Base API setup
FORUMSCOUT_API_KEY = os.getenv("FORUMSCOUT_API_KEY")  
APIFY_CLIENT_TOKEN = os.getenv("APIFY_CLIENT_TOKEN")
BASE_URL = "https://forumscout.app/api"

# ForumScout Endpoints found here: https://forumscout.app/developers 
# ENDPOINTS = {
#     # "twitter": "x_search",
#     # "reddit_posts": "reddit_posts_search",
#     # "reddit_comments": "reddit_comments_search",
#     # "youtube": "youtube_search",
#     # "linkedin": "linkedin_search",
#     # "youtube" "youtube_search",
#     "instagram": "instagram_search",
#     "tiktok": "tiktok"
# }

def fetch_forumscout_data(endpoint, keyword, sort_by=None, recency=None):
    url = f"{BASE_URL}/{endpoint}"
    headers = {
        "X-API-Key": FORUMSCOUT_API_KEY
    }
    params = {
        "keyword": keyword,
        "sort_by": sort_by,
        "upload_date": recency
    }
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        print(f"Fetched {keyword} from {endpoint}!")
        # log_to_browser(f"Fetched {keyword} from {endpoint}!")
        return response.json()
    else:
        print(f"Error fetching {keyword} from {endpoint}: {response.status_code}")
        # log_to_browser(f"Error fetching {keyword} from {endpoint}: {response.status_code}")
        return []


def normalize_result(post, platform, keyword):
    print(f"Normalizing result for {post} from {platform} with keyword {keyword}")
    # log_to_browser(f"Normalizing result for {post.get("url")} from {platform} with keyword {keyword}")
    return {
        "platform": platform,
        "keyword": keyword,
        "content": post.get("text") or post.get("content") or post.get('snippet') or "",
        "author": post.get("username") or post.get("author") or "",
        "timestamp": post.get("date") or post.get("published_at") or datetime.utcnow().isoformat(),
        "url": post.get("url") or post.get("link") or ""
    }

def write_to_csv(records, output_file):
    if not records:
        print("No records to write.")
        # log_to_browser(f"No records to write to {output_file}")
        return

    keys = records[0].keys()
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        if f.tell() == 0:
            writer.writeheader()
        writer.writerows(records)
        print(f"Successfully added records to {output_file}")
        # log_to_browser(f"Successfully added records to {output_file}")

def safe_read_csv(path):
    try:
        if os.path.getsize(path) > 0:
            return pd.read_csv(path)
    except Exception:
        pass
    return None  # return None if file is empty or invalid

def run_ingestion(keywords, endpoints, sort_by=None, recency=None, output_file="output/forumscout_data.csv"):
    all_records = []
    temp_file = 'output/forumscout_data_temp.csv'
    open("output/tiktok_data.csv", "w").close() # Clears tiktok file

    for platform, endpoint in endpoints.items():
        if platform == 'tiktok':
            if sort_by == 'Latest':
                sort_by = 'latest'
            scrape_tiktok_data(APIFY_CLIENT_TOKEN, keywords, sort_by, recency)
        else:
            for keyword in keywords:
                print(f"🔎 Fetching '{keyword}' from {platform}...")
                # log_to_browser(f"🔎 Fetching '{keyword}' from {platform}...")
                if sort_by is not None:
                    if sort_by == "Latest":
                        if platform == "instagram":
                            sort_by = "recent"
                        elif platform == "reddit_posts":
                            sort_by = "new"
                        elif platform == "reddit_comments":
                            sort_by = "created_utc"
                    else: # It was sorted by popularity
                        if platform == "instagram" or platform == "reddit_posts":
                            sort_by = "top"
                        elif platform == "reddit_comments":
                            sort_by = "score"
                if recency is not None:
                    recency.replace(" ", "_")
                    print(recency)
                posts = fetch_forumscout_data(endpoint, keyword, sort_by, recency)
                normalized = [normalize_result(p, platform, keyword) for p in posts]
                all_records.extend(normalized)
                time.sleep(1)  # avoid rate limits

    open(temp_file, "w").close() # Clears temp file
    open(output_file, "w").close() # Clears output file
    
    write_to_csv(all_records, temp_file) 
    
    # Read both files safely
    df1 = safe_read_csv(temp_file)
    df2 = safe_read_csv("output/tiktok_data.csv")

    # Determine what to save as output
    if df1 is not None and df2 is not None:
        combined_df = pd.concat([df1, df2], ignore_index=True)
        combined_df.to_csv(output_file, index=False)
        print("✅ Both files had content. Merged and saved.")
    elif df1 is not None:
        df1.to_csv(output_file, index=False)
        print("✅ Only temp_file had content. Saved as output.")
    elif df2 is not None:
        df2.to_csv(output_file, index=False)
        print("✅ Only tiktok_data.csv had content. Saved as output.")

    print(f"✅ Ingested records into {output_file}.")
    # log_to_browser(f"✅ Ingested {len(pd.read_csv(output_file))} records into {output_file}.")

# if __name__ == "__main__":
#     import os
#     # os.makedirs("output", exist_ok=True)
#     run_ingestion(KEYWORDS, ENDPOINTS)
