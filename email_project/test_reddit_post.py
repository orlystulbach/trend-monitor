import os
import praw
import re

def make_reddit_client():
    return praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        refresh_token=os.getenv("REDDIT_REFRESH_TOKEN"),
        user_agent="trend-monitor:trend-monitoring:0.1 (by /u/your_reddit_username)",
    )

def fetch_reddit_post_api(url: str):
    def _extract_submission_id(u: str):
        for pat in (r"/comments/([a-z0-9]{5,8})", r"redd\.it/([a-z0-9]{5,8})"):
            m = re.search(pat, u, re.I)
            if m:
                return m.group(1)
        return None

    sub_id = _extract_submission_id(url)
    if not sub_id:
        print(f"[Reddit API] Could not parse submission id from: {url}")
        return None, None

    reddit = make_reddit_client()
    sub = reddit.submission(id=sub_id)
    title = sub.title or ""
    body = sub.selftext or ""
    return title, body

if __name__ == "__main__":
    # Test with any public Reddit post
    url = "https://www.reddit.com/r/IsraelPalestine/comments/1mo42i1/the_range_of_antizionist_ideology/"
    title, body = fetch_reddit_post_api(url)
    print("Title:", title)
    print("Body:", body[:300] + "..." if body else "[No body]")
