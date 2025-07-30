from bertopic import BERTopic
from sentence_transformers import SentenceTransformer
import pandas as pd
from collections import Counter

df = pd.read_csv("output/forumscout_cleaned_data.csv")

# Load a PyTorch-based multilingual model
embedding_model = SentenceTransformer("distiluse-base-multilingual-cased-v1")  # or "all-MiniLM-L6-v2"

captions = df["cleaned_caption"].fillna("").astype(str).tolist()
topic_model = BERTopic(
    language="multilingual",
    embedding_model=embedding_model,
    calculate_probabilities=True  # optional
)
topics, probs = topic_model.fit_transform(captions) 
  # get two key outputs: topics and probs
  # topics -- refers to the topic number assigned to each caption
  # probs -- refers to the confidence score

# Add topics to new dataframe and save to new csv file
df["topic"] = topics
df.to_csv("output/forumscout_with_topics.csv", index=False, encoding="utf-8-sig")

topic_info = topic_model.get_topic_info()  # DataFrame: topic id, count, top words
topic_info.to_csv("output/topic_summary.csv", index=False)

topic_info = topic_model.get_topic_info()
print(topic_info)
print(Counter(topics))

# topic_model.get_topic_info()
# topic_model.get_topic(0)  # shows most common words in that topic
