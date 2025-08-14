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
from pathlib import Path

# Load environment variables
load_dotenv()

# Project root = parent of project_code
PROJECT_ROOT = Path(__file__).resolve().parents[1]          # .../trend_monitoring
OUTPUT_DIR   = Path(os.getenv("OUTPUT_DIR", PROJECT_ROOT / "output")).resolve()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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

# def safe_read_csv(path):
#     try:
#         if os.path.getsize(path) > 0:
#             return pd.read_csv(path)
#     except Exception:
#         pass
#     return None  # return None if file is empty or invalid

def safe_read_csv(path):
    p = Path(path)
    print("path", path)
    try:
        if not p.exists() or p.stat().st_size == 0:
            print(f"[safe_read_csv] Empty or missing: {p}")
            return None
        df = pd.read_csv(
            p,
            engine="python",
            encoding="utf-8-sig",
            on_bad_lines="skip",
            dtype=str,
        )
        if df is None or df.shape[1] == 0:
            print(f"[safe_read_csv] No columns parsed: {p}")
            return None
        
        # Remove duplicate header rows sometimes appended by scrapers
        header_map = dict(zip(df.columns, df.columns))
        df = df[~df.apply(lambda r: all(str(r[c]) == str(header_map[c]) for c in df.columns), axis=1)]

        # Normalize column names
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        df = df.reset_index(drop=True)
        print(f"[safe_read_csv] Loaded {len(df)} rows, {len(df.columns)} cols from {p}")
        return df
    except Exception as e:
        print(f"[safe_read_csv] python engine failed ({e}); trying fallback…")
        try:
            # Fallback: C engine (fast). If your pandas is old and
            # doesn't support on_bad_lines with C, remove that kw.
            df = pd.read_csv(
                p,
                encoding="utf-8-sig",
                on_bad_lines="skip",
                dtype=str
            )
        except Exception as e2:
            print(f"[safe_read_csv] Fallback failed: {e2}")
            return None

def merge_union(df_a, df_b):
    if df_a is not None and df_b is not None:
        cols = sorted(set(df_a.columns) | set(df_b.columns))
        print("✅ Both files had content. Merged and saved.")
        return pd.concat([df_a.reindex(columns=cols), df_b.reindex(columns=cols)], ignore_index=True)
    return df_a if df_a is not None else df_b

def run_ingestion(keywords, endpoints, sort_by=None, recency=None, output_file=OUTPUT_DIR / "forumscout_data.csv"):
    all_records = []

    TEMP_CSV = OUTPUT_DIR / "forumscout_data_temp.csv"
    TIKTOK_CSV = OUTPUT_DIR / "tiktok_data.csv"

    # Clear all files
    TIKTOK_CSV.write_text("")
    TEMP_CSV.write_text("") # Clears temp file
    open(output_file, "w").close() # Clears output file

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
    
    write_to_csv(all_records, str(TEMP_CSV)) 
    
    # Read both files safely
    # df1 = safe_read_csv(str(TEMP_CSV))
    # df2 = safe_read_csv(str(TIKTOK_CSV))
    df_forum = safe_read_csv(TEMP_CSV)
    df_tt = safe_read_csv(TIKTOK_CSV)

    print("TEMP rows:", 0 if df_forum is None else len(df_forum))
    print("TT rows:", 0 if df_tt is None else len(df_tt))

    out_df = merge_union(df_forum, df_tt)

    if out_df is None or out_df.empty:
        out_df = pd.DataFrame([])
    
    out_df.to_csv(output_file, index=False)

    # Determine what to save as output
    # if df1 is not None and df2 is not None:
    #     combined_df = pd.concat([df1, df2], ignore_index=True)
    #     combined_df.to_csv(output_file, index=False)
    #     print("✅ Both files had content. Merged and saved.")
    # elif df1 is not None:
    #     df1.to_csv(output_file, index=False)
    #     print("✅ Only temp_file had content. Saved as output.")
    # elif df2 is not None:
    #     df2.to_csv(output_file, index=False)
    #     print("✅ Only tiktok_data.csv had content. Saved as output.")

    # print(f"✅ Ingested records into {output_file}.")
    print(f"✅ Saved {0 if out_df is None else len(out_df)} rows to {output_file}")
    # log_to_browser(f"✅ Ingested {len(pd.read_csv(output_file))} records into {output_file}.")

# if __name__ == "__main__":
#     import os
#     # os.makedirs("output", exist_ok=True)
#     run_ingestion(KEYWORDS, ENDPOINTS)
