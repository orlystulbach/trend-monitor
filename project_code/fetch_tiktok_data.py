from apify_client import ApifyClient
import csv
from utils.logger import log_to_browser

def scrape_tiktok_data(apify_token, keywords: list, output_file = 'output/tiktok_data.csv'):
  # Initialize the ApifyClient with your API token
  client = ApifyClient(apify_token)

  # Prepare CSV file
  with open(output_file, mode="w", newline="", encoding="utf-8") as csvfile:
      writer = csv.DictWriter(csvfile, fieldnames=["platform", "keyword", "content", "author", "timestamp", "url"])
      writer.writeheader()

      for keyword in keywords:
        # Prepare the Actor input
        print(f"🔎 Fetching '{keyword}' from TikTok...")

        run_input = {
            "hashtags": [keyword],
            "resultsPerPage": 25,
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
              writer.writerow({
                  "platform": "tiktok",
                  "keyword": keyword,
                  "content": item.get("text", ""),  # video description/caption
                  "author": item.get("authorMeta.name", {}).get("name", ""),  # username
                  "timestamp": item.get("createTimeISO", ""),  # ISO timestamp
                  "url": item.get("webVideoUrl", ""),  # video URL
              })

          print(f"Added {item} to {output_file}")

        except Exception as e:
          print(f"❌ Error scraping keyword '{keyword}': {e}")
      
      # print(f"Added {len(dataset_items)} to {output_file}")
      # log_to_browser(f"Added {len(dataset_items)} to {output_file}")