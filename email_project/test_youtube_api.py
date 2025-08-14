import os
import requests

# Ensure your key is set as an environment variable
api_key = os.getenv("YOUTUBE_API_KEY")
if not api_key:
    raise RuntimeError("❌ YOUTUBE_API_KEY is not set in environment variables.")

# Pick any known video
video_id = "dQw4w9WgXcQ"  # You can replace this with any video ID

url = (
    f"https://www.googleapis.com/youtube/v3/videos"
    f"?part=snippet&id={video_id}&key={api_key}"
)

try:
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    if "items" in data and len(data["items"]) > 0:
        title = data["items"][0]["snippet"]["title"]
        print(f"✅ API key works! Video title: {title}")
    else:
        print(f"⚠️ API key works, but video not found: {video_id}")

except requests.exceptions.HTTPError as e:
    print(f"❌ HTTP Error: {e.response.status_code} {e.response.text}")
except Exception as e:
    print(f"❌ Unexpected error: {e}")
