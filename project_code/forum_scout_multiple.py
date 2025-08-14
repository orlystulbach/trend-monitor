import os
import requests
import time
import csv
import datetime as dt
from dotenv import load_dotenv
# from utils.logger import log_to_browser
from project_code.fetch_tiktok_data import scrape_tiktok_data
import pandas as pd
from pathlib import Path

# ----------------------------
# Environment & Paths
# ----------------------------
load_dotenv()

# Project root = parent of project_code
PROJECT_ROOT = Path(__file__).resolve().parents[1]          # .../trend_monitoring
OUTPUT_DIR   = Path(os.getenv("OUTPUT_DIR", PROJECT_ROOT / "output")).resolve()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ----------------------------
# API Config
# ----------------------------
FORUMSCOUT_API_KEY = os.getenv("FORUMSCOUT_API_KEY")
APIFY_CLIENT_TOKEN = os.getenv("APIFY_CLIENT_TOKEN")
BASE_URL = "https://forumscout.app/api"

# Example endpoints (you likely pass these in externally):
# ENDPOINTS = {
#     "instagram": "instagram_search",
#     "reddit_posts": "reddit_posts_search",
#     "reddit_comments": "reddit_comments_search",
#     "x_search": "x_search",
#     "tiktok": "tiktok"
# }

# ----------------------------
# Helpers
# ----------------------------
def fetch_forumscout_data(endpoint, keyword, sort_by=None, recency=None):
    url = f"{BASE_URL}/{endpoint}"
    headers = {"X-API-Key": FORUMSCOUT_API_KEY}
    params = {
        "keyword": keyword,
        "sort_by": sort_by,
        "upload_date": recency
    }
    response = requests.get(url, headers=headers, params=params, timeout=60)
    if response.status_code == 200:
        print(f"Fetched {keyword} from {endpoint}!")
        # log_to_browser(f"Fetched {keyword} from {endpoint}!")
        return response.json()
    else:
        print(f"Error fetching {keyword} from {endpoint}: {response.status_code}")
        # log_to_browser(f"Error fetching {keyword} from {endpoint}: {response.status_code}")
        return []

def normalize_result(post, platform, keyword):
    # print(f"Normalizing result for {platform} with keyword {keyword}")
    # log_to_browser(f'Normalizing result for {post.get("url")} from {platform} with keyword {keyword}')
    return {
        "platform": platform,
        "keyword": keyword,
        "content": post.get("text") or post.get("content") or post.get("snippet") or "",
        "author": post.get("username") or post.get("author") or "",
        "timestamp": (
            post.get("date")
            or post.get("published_at")
            or post.get("timestamp")
            or post.get("created_at")
            or dt.datetime.utcnow().isoformat()
        ),
        "url": post.get("url") or post.get("link") or ""
    }

def write_to_csv(records, output_file):
    if not records:
        print("No records to write.")
        # log_to_browser(f"No records to write to {output_file}")
        return
    keys = list(records[0].keys())
    os.makedirs(os.path.dirname(str(output_file)), exist_ok=True)
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        if f.tell() == 0:
            writer.writeheader()
        writer.writerows(records)
        print(f"Successfully added records to {output_file}")
        # log_to_browser(f"Successfully added records to {output_file}")

def safe_read_csv(path):
    p = Path(path)
    print("[safe_read_csv] path:", p)
    try:
        if not p.exists() or p.stat().st_size == 0:
            print(f"[safe_read_csv] Empty or missing: {p}")
            return None
        df = pd.read_csv(
            p,
            engine="python",         # tolerant parser
            encoding="utf-8-sig",    # strip BOM if present
            on_bad_lines="skip",     # skip malformed lines
            dtype=str
        )
        if df is None or df.shape[1] == 0:
            print(f"[safe_read_csv] No columns parsed: {p}")
            return None

        # Remove duplicate header rows that some scrapers append
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
            df = pd.read_csv(
                p,
                encoding="utf-8-sig",
                on_bad_lines="skip",
                dtype=str
            )
            # Same cleanup
            header_map = dict(zip(df.columns, df.columns))
            df = df[~df.apply(lambda r: all(str(r[c]) == str(header_map[c]) for c in df.columns), axis=1)]
            df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
            return df.reset_index(drop=True)
        except Exception as e2:
            print(f"[safe_read_csv] Fallback failed: {e2}")
            return None

def merge_union(df_a, df_b):
    if df_a is not None and df_b is not None:
        cols = sorted(set(df_a.columns) | set(df_b.columns))
        merged = pd.concat(
            [df_a.reindex(columns=cols), df_b.reindex(columns=cols)],
            ignore_index=True
        )
        print("✅ Both sources had content. Merged.")
        return merged
    return df_a if df_a is not None else df_b

def _coerce_to_datetime_utc(series: pd.Series) -> pd.Series:
    """
    Accepts ISO strings or Unix epoch (seconds or ms) and returns UTC datetimes.
    """
    s = pd.to_numeric(series, errors="coerce")
    if s.notna().any():
        # anything >= 1e12 is probably ms
        s = s.where(s < 1e12, s / 1000.0)
        return pd.to_datetime(s, unit="s", utc=True, errors="coerce")
    return pd.to_datetime(series, utc=True, errors="coerce")

def filter_recent_posts(
    df: pd.DataFrame,
    months: int = 3,
    candidate_date_cols = (
        "posted_at", "timestamp", "created_utc", "create_time",
        "created_at", "published_at", "date", "datetime", "time"
    )
) -> pd.DataFrame:
    """
    Keeps only rows whose post date is within the last `months` calendar months.
    If no recognizable date column exists, returns df unchanged.
    """
    if df is None or df.empty:
        return df

    df = df.copy()
    # Find first date-like column you have
    date_col = next((c for c in candidate_date_cols if c in df.columns), None)
    if not date_col:
        print("[filter_recent_posts] No date column found; leaving df unchanged.")
        return df

    df["_posted_at_utc"] = _coerce_to_datetime_utc(df[date_col])
    cutoff = pd.Timestamp.now(tz="UTC") - pd.DateOffset(months=months)
    recent = df[df["_posted_at_utc"] >= cutoff].drop(columns=["_posted_at_utc"])
    # Drop rows where we couldn't parse a date
    recent = recent[recent[date_col].notna()].reset_index(drop=True)

    print(f"[filter_recent_posts] Kept {len(recent)}/{len(df)} rows since {cutoff.date()}.")
    return recent

def map_sort_for_platform(platform: str, choice: str | None) -> str | None:
    """
    Map your human-facing sort choice (e.g., 'Latest', 'Top') into the platform's expected value.
    """
    if not choice:
        return None
    if choice == "Latest":
        return {
            "instagram": "recent",
            "reddit_posts": "new",
            "reddit_comments": "created_utc",
            "x_search": "Latest",    # if ForumScout expects "Latest" literally
            "tiktok": "latest"
        }.get(platform, None)
    # Popularity / Top
    return {
        "instagram": "top",
        "reddit_posts": "top",
        "reddit_comments": "score",
        "x_search": "Top",
        "tiktok": "top"
    }.get(platform, None)

# ----------------------------
# Main ingestion (single-pass)
# ----------------------------
def run_ingestion(
    keywords,
    endpoints,                      # e.g. {"instagram":"instagram_search", "tiktok":"tiktok", ...}
    sort_by: str = "Latest",
    recency: str | None = None,
    output_file: Path | str = OUTPUT_DIR / "forumscout_data.csv"
):
    output_file = Path(output_file)
    TEMP_CSV   = OUTPUT_DIR / "forumscout_data_temp.csv"
    TIKTOK_CSV = OUTPUT_DIR / "tiktok_data.csv"

    # Fresh run
    TEMP_CSV.write_text("")
    TIKTOK_CSV.write_text("")
    output_file.write_text("")

    all_records = []
    recency_in = recency.replace(" ", "_") if isinstance(recency, str) else recency

    # >>> STRICT SEQUENTIAL: platform × keyword <<<
    for platform, endpoint in endpoints.items():
        for keyword in keywords:
            sb = map_sort_for_platform(platform, sort_by)

            if platform == "tiktok":
                print(f"🎵 TikTok | kw='{keyword}' | sort_by={sb} | recency={recency_in}")
                # Try to force writing to our known CSV; fall back to legacy signatures
                try:
                    scrape_tiktok_data(APIFY_CLIENT_TOKEN, keyword, sb, recency_in, save_csv=str(TIKTOK_CSV))
                except TypeError:
                    try:
                        # some versions expect a list of keywords
                        scrape_tiktok_data(APIFY_CLIENT_TOKEN, [keyword], sb, recency_in)
                    except TypeError:
                        # some expect single keyword but no save_csv
                        scrape_tiktok_data(APIFY_CLIENT_TOKEN, keyword, sb, recency_in)
                time.sleep(1)  # rate-limit per task
                continue

            # Non-TikTok (ForumScout)
            print(f"🔎 {platform} | kw='{keyword}' | sort_by={sb} | recency={recency_in}")
            posts = fetch_forumscout_data(endpoint, keyword, sb, recency_in)
            normalized = [normalize_result(p, platform, keyword) for p in posts]
            all_records.extend(normalized)
            time.sleep(1)

    # Write ForumScout temp if any
    if all_records:
        write_to_csv(all_records, str(TEMP_CSV))

    # Read, filter last 3 months, and merge
    df_forum = filter_recent_posts(safe_read_csv(TEMP_CSV), months=3)
    df_tt    = filter_recent_posts(safe_read_csv(TIKTOK_CSV), months=3)

    print("TEMP rows:", 0 if df_forum is None else len(df_forum))
    print("TT   rows:", 0 if df_tt    is None else len(df_tt))

    out_df = merge_union(df_forum, df_tt)
    if out_df is None or out_df.empty:
        out_df = pd.DataFrame([])
    out_df.to_csv(output_file, index=False)
    print(f"✅ Saved {len(out_df)} rows to {output_file}")