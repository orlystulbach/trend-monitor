
import pandas as pd
import re
from tqdm import tqdm

def clean_captions_file(input_file, output_file, st=None):
    df = pd.read_csv(input_file)

    def clean_caption(text):
        if not isinstance(text, str):
            return ""
        text = re.sub(r"[^\w\s#@]", "", text.lower())
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    tqdm.pandas()
    df["cleaned_caption"] = df["caption"].fillna("").progress_apply(clean_caption)
    df.to_csv(output_file, index=False, encoding="utf-8-sig")
    # if st:
    #     st.success(f"✅ Cleaned captions saved to {output_file}")

if __name__ == "__main__":
    input_file = "output/forumscout_data_with_captions_2.csv"
    output_file = "output/forumscout_cleaned_data_2.csv"
    clean_captions_file(input_file, output_file)