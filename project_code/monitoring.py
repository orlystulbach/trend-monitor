# social_monitoring_pipeline/main.py

import tweepy
import requests
import csv
from transformers import pipeline
from datetime import datetime
import os

# Load environment variables (e.g., from .env file)
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")

KEYWORDS = ["gaza", "jews", "zionism"]
CSV_FILE = "output/social_data.csv"

# Initialize sentiment analysis models
sentiment_model = pipeline(
    "sentiment-analysis", 
    model="distilbert-base-uncased-finetuned-sst-2-english", 
    framework="pt"  # Force PyTorch
)
emotion_model = pipeline("text-classification", model="j-hartmann/emotion-english-distilroberta-base", framework="pt")

def write_to_csv(data):
    header = list(data.keys())
    file_exists = os.path.isfile(CSV_FILE)
    with open(CSV_FILE, mode="a", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=header)
        if not file_exists:
            writer.writeheader()
        writer.writerow(data)

def enrich_user(user_id):
    # Stub: implement Twitter user enrichment if needed
    return {
        "user_id": user_id,
        "gender": "unknown",
        "location": "unknown"
    }

def analyze_text(text):
    sentiment = sentiment_model(text)[0]
    emotion = emotion_model(text)[0]
    return sentiment, emotion

class MyStream(tweepy.StreamingClient):
    def on_tweet(self, tweet):
        if tweet.lang != "en":
            return
        try:
            sentiment, emotion = analyze_text(tweet.text)
            enriched_user = enrich_user(tweet.author_id)

            row = {
                "timestamp": datetime.utcnow().isoformat(),
                "text": tweet.text,
                "sentiment": sentiment["label"],
                "sentiment_score": sentiment["score"],
                "emotion": emotion["label"],
                "emotion_score": emotion["score"],
                "user_id": enriched_user["user_id"],
                "gender": enriched_user["gender"],
                "location": enriched_user["location"]
            }
            write_to_csv(row)
            print("Recorded:", row)
        except Exception as e:
            print("Error processing tweet:", e)


def main():
    stream = MyStream(bearer_token=TWITTER_BEARER_TOKEN)

    print("Adding rules...")
    for rule in stream.get_rules().data or []:
        stream.delete_rules(rule.id)
    stream.add_rules(tweepy.StreamRule(" OR ".join(KEYWORDS)))

    print("Starting stream...")
    stream.filter(tweet_fields=["author_id", "lang", "created_at"], expansions=["author_id"])

if __name__ == "__main__":
    os.makedirs("output", exist_ok=True)
    main()
