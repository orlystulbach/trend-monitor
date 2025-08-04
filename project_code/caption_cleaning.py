# from tqdm import tqdm
# import pandas as pd
# import re
# import os

# # Load your CSV
# # df = pd.read_csv("output/forumscout_data_with_captions.csv")

# # Clean captions: lowercase, remove emojis/symbols/extra whitespace
# def clean_caption(text):
    
#     if not isinstance(text, str):
#         return ""
#     # Remove punctuation except hashtags & mentions
#     text = re.sub(r"[^\w\s#@]", "", text.lower())
#     # Remove multiple spaces
#     text = re.sub(r"\s+", " ", text)
#     return text.strip()

# # # Apply cleaner
# # tqdm.pandas()
# # df["cleaned_caption"] = df["caption"].fillna("").progress_apply(clean_caption)

# # # Save cleaned output to a new file
# # df.to_csv("output/forumscout_cleaned_data.csv", index=False, encoding="utf-8-sig")

# # print("✅ Cleaned captions saved to output/forumscout_cleaned_data.csv")

# def clean_captions_file(input_file, output_file, st=None):
#     if not os.path.exists(input_file):
#         raise FileNotFoundError(f"File not found: {input_file}")

#     df = pd.read_csv(input_file)

#     if st:
#         st.info("Cleaning captions...")
#         progress = st.progress(0)
#         status = st.empty()

#         total = len(df)
#         cleaned = []

#         for i, caption in enumerate(df["caption"].fillna("")):
#             cleaned_text = clean_caption(caption)
#             cleaned.append(cleaned_text)
#             progress.progress((i + 1) / total)
#             if i % 5 == 0:
#                 status.text(f"Processing caption {i+1} of {total}")

#         df["cleaned_caption"] = cleaned
#         progress.progress(1.0)
#         status.text("Done!")

#     else:
#         df["cleaned_caption"] = df["caption"].fillna("").apply(clean_caption)

#     os.makedirs(os.path.dirname(output_file), exist_ok=True)
#     df.to_csv(output_file, index=False, encoding="utf-8-sig")

#     if st:
#         st.success(f"✅ Cleaned captions saved to {output_file}")
#     else:
#         print(f"✅ Cleaned captions saved to {output_file}")

def clean_captions_file(input_file, output_file, st=None):
    import pandas as pd
    import re
    from tqdm import tqdm

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