from apify_client import ApifyClient
import csv
from utils.logger import log_to_browser
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # go up to project root
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TIKTOK_CSV = OUTPUT_DIR / "tiktok_data.csv"

def scrape_tiktok_data(apify_token, keywords: list, sort_by="latest", recency=None, output_file = str(TIKTOK_CSV)):
  # Initialize the ApifyClient with your API token
  client = ApifyClient(apify_token)

  if sort_by == 'Most Popular':
     sort_by = 'popular'

  # Prepare CSV file
  with open(output_file, mode="w", newline="", encoding="utf-8") as csvfile:
      writer = csv.DictWriter(csvfile, fieldnames=["platform", "keyword", "content", "author", "timestamp", "url"])
      writer.writeheader()

      for keyword in keywords:
        # Prepare the Actor input
        print(f"🔎 Fetching '{keyword}' from TikTok based on {sort_by}...")

        run_input = {
            "hashtags": [keyword],
            "resultsPerPage": 25,
            "profileSorting": sort_by,
            "proxyCountryCode": "None",
        }

        try: 
          # Run the Actor and wait for it to finish
          run = client.actor("clockworks/tiktok-scraper").call(run_input=run_input)

          # Dataset ID for the run
          dataset_id = run["defaultDatasetId"]
          print('fetched tiktok data')
          dataset_items = client.dataset(dataset_id).iterate_items()

          for item in dataset_items:
              author_meta = item.get("authorMeta") or {}
              author = (
                  author_meta.get("name") or          # handle/username
                  author_meta.get("uniqueId") or      # sometimes used
                  author_meta.get("nickName") or ""   # display name fallback
              )

              writer.writerow({
                  "platform": "tiktok",
                  "keyword": keyword,
                  "content": item.get("text", ""),  # video description/caption
                  # "author": item.get("authorMeta.name", {}).get("name", ""),  # username
                  "author": author,
                  "timestamp": item.get("createTimeISO", ""),  # ISO timestamp
                  "url": item.get("webVideoUrl", ""),  # video URL
              })

          print(f"Added {item} to {output_file}")

        except Exception as e:
          print(f"❌ Error scraping keyword '{keyword}': {e}")
      
      # print(f"Added {len(dataset_items)} to {output_file}")
      # log_to_browser(f"Added {len(dataset_items)} to {output_file}")