from tqdm import tqdm
import pandas as pd
import re

# Load your CSV
df = pd.read_csv("output/forumscout_data_with_captions.csv")

# Clean captions: lowercase, remove emojis/symbols/extra whitespace
def clean_caption(text):
    
    if not isinstance(text, str):
        return ""
    # Remove punctuation except hashtags & mentions
    text = re.sub(r"[^\w\s#@]", "", text.lower())
    # Remove multiple spaces
    text = re.sub(r"\s+", " ", text)
    return text.strip()

# Apply cleaner
tqdm.pandas()
df["cleaned_caption"] = df["caption"].fillna("").progress_apply(clean_caption)

# Save cleaned output to a new file
df.to_csv("output/forumscout_cleaned_data.csv", index=False, encoding="utf-8-sig")

print("✅ Cleaned captions saved to output/forumscout_cleaned_data.csv")
