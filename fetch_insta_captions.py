import instaloader
import csv
import re

# Initialize Instaloader
L = instaloader.Instaloader()

def extract_shortcode(url):
    match = re.search(r"/p/([A-Za-z0-9_-]+)", url)
    return match.group(1) if match else None

def fetch_caption(shortcode):
    try:
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        return post.caption
    except Exception as e:
        print(f"Error fetching caption for {shortcode}: {e}")
        return ""

input_file = "output/forumscout_data.csv"
output_file = "output/forumscout_data_with_captions.csv"

with open(input_file, newline='') as infile, open(output_file, 'w', newline='') as outfile:
    reader = csv.DictReader(infile)
    fieldnames = reader.fieldnames + ["caption"]
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()

    for row in reader:
        if row["platform"] == "instagram" and row["url"]:
            shortcode = extract_shortcode(row["url"])
            if shortcode:
                caption = fetch_caption(shortcode)
                row["caption"] = caption
            else:
                row["caption"] = ""
        else:
            row["caption"] = ""
        writer.writerow(row)

print(f"✅ Captions added. Enriched data saved to {output_file}")
