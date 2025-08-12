import csv
from pathlib import Path

# import your real function
from email_fetch_captions import enrich_captions

# IN = Path("tmp_input.csv")
OUT = Path("tmp_output.csv")

# 1) write a tiny sample input CSV
# rows = [
#     {
#         "platform": "reddit_posts",
#         "keyword": "israel",
#         "content": "This is the reddit snippet/content here",
#         "author": "u_example",
#         "timestamp": "2024-01-01T00:00:00Z",
#         "url": "https://www.reddit.com/r/news/comments/xxxxxx/example_post/",
#         "caption": "",
#         "body": "",
#     },
#     {
#         "platform": "tiktok",
#         "keyword": "campus",
#         "content": "tiktok video caption here",
#         "author": "creator123",
#         "timestamp": "2024-01-02T00:00:00Z",
#         "url": "https://www.tiktok.com/@creator/video/123456",
#         "caption": "",
#         "body": "",
#     },
#     {
#         "platform": "instagram",
#         "keyword": "sports",
#         "content": "",
#         "author": "someone",
#         "timestamp": "2024-01-03T00:00:00Z",
#         "url": "https://www.instagram.com/p/SHORTCODE/",
#         "caption": "",
#         "body": "",
#     },
#     {
#         "platform": "youtube",
#         "keyword": "news",
#         "content": "",
#         "author": "channel",
#         "timestamp": "2024-01-04T00:00:00Z",
#         "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
#         "caption": "",
#         "body": "",
#     },
# ]

# fields = ["platform","keyword","content","author","timestamp","url","caption","body"]
# with IN.open("w", newline="", encoding="utf-8") as f:
#     w = csv.DictWriter(f, fieldnames=fields)
#     w.writeheader()
#     for r in rows:
#         w.writerow(r)

# 2) run the enrichment (no Streamlit UI in this test)
enrich_captions("TEST_forumscout_data.csv", str(OUT), st=None)

# 3) show the results
print("----- Enriched CSV preview -----")
with OUT.open("r", encoding="utf-8") as f:
    print(f.read())