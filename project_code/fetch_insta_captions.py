import instaloader
import csv
import re
import os
import streamlit as st

# Initialize Instaloader
# L = instaloader.Instaloader()

def extract_shortcode(url):
    match = re.search(r"/p/([A-Za-z0-9_-]+)", url)
    return match.group(1) if match else None

# def fetch_caption(shortcode):
#     try:
#         post = instaloader.Post.from_shortcode(L.context, shortcode)
#         return post.caption
#     except Exception as e:
#         print(f"Error fetching caption for {shortcode}: {e}")
#         return ""
def fetch_caption(shortcode, loader):
    try:
        post = instaloader.Post.from_shortcode(loader.context, shortcode)
        return post.caption
    except Exception as e:
        print(f"Error fetching caption for {shortcode}: {e}")
        return ""
    
# input_file = "output/forumscout_data.csv"
# output_file = "output/forumscout_data_with_captions.csv"

# with open(input_file, newline='') as infile, open(output_file, 'w', newline='') as outfile:
#     reader = csv.DictReader(infile)
#     fieldnames = reader.fieldnames + ["caption"]
#     writer = csv.DictWriter(outfile, fieldnames=fieldnames)
#     writer.writeheader()

#     for row in reader:
#         if row["platform"] == "instagram" and row["url"]:
#             shortcode = extract_shortcode(row["url"])
#             if shortcode:
#                 caption = fetch_caption(shortcode)
#                 row["caption"] = caption
#             else:
#                 row["caption"] = ""
#         else:
#             row["caption"] = ""
#         writer.writerow(row)

# print(f"✅ Captions added. Enriched data saved to {output_file}")

def enrich_instagram_captions(input_file, output_file):
    # Initialize Instaloader only once
    L = instaloader.Instaloader()

    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Input file not found: {input_file}")

    with open(input_file, newline='', encoding='utf-8') as infile, open(output_file, 'w', newline='', encoding='utf-8') as outfile:
        reader = csv.DictReader(infile)
        # reader_list = list(reader)
        fieldnames = reader.fieldnames + ["caption"]
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()

        # for row in reader:
        #     if row["platform"] == "instagram" and row["url"]:
        #         shortcode = extract_shortcode(row["url"])
        #         if shortcode:
        #             caption = fetch_caption(shortcode, L)
        #             row["caption"] = caption
        #         else:
        #             row["caption"] = ""
        #     else:
        #         row["caption"] = ""
        #     writer.writerow(row)
        # Streamlit progress bar
        # total = len(reader_list)
        # progress = st.progress(0) if st else None

        for i, row in enumerate(reader):
            if row["platform"] == "instagram" and row["url"]:
                shortcode = extract_shortcode(row["url"])
                row["caption"] = fetch_caption(shortcode, L) if shortcode else ""
            else:
                row["caption"] = ""
            writer.writerow(row)

            # if progress:
            #     progress.progress((i + 1) / total)

    # st.success(f"✅ Captions added to {output_file}")
    
    print(f"✅ Captions added. Enriched data saved to {output_file}")


if __name__ == "__main__":
    enrich_instagram_captions("output/forumscout_data_2.csv", "output/forumscout_data_with_captions_2.csv")
