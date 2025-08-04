import openai
import pandas as pd
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

client = openai.OpenAI()

def generate_chunked_summaries(
    # === CONFIGURATION ===
  INPUT_FILE = "output/forumscout_cleaned_data_2.csv",
  OUTPUT_FILE = "output/gpt_narrative_summary_2.md",
  CHUNK_SIZE = 30,
  OPENAI_MODEL = "gpt-4"
  # OPENAI_MODEL = "gpt-3_5-turbo-instruct"
):

  # === Load and clean data ===
  df = pd.read_csv(INPUT_FILE) # Loads csv file of cleaned data into dataframe
  df = df[df["cleaned_caption"].notnull() & df["cleaned_caption"].str.strip().ne("")] # Removes rows where cleaned_caption is NaN or empty

  # Format posts for GPT prompt
  posts = df[["cleaned_caption", "author", "url"]].to_dict(orient="records")

  # Generator function: yields slices of post list
  def chunk_posts(posts, size):
    for i in range(0, len(posts), size):
      yield posts[i:i + size]
    
  # === OpenAI helper ===
  def format_prompt(post_chunk):
    formatted = "\n".join([
        f"- @{p['author']}: \"{p['cleaned_caption'].strip()}\" ({p['url']})"
        for p in post_chunk
    ])
    prompt = f""" 
  You are a social media analyst reviewing Instagram captions about humanitarian and political issues in Gaza.
  Your job is to:
  1. Identify and name distinct narratives or conversation themes.
  2. Write a 2 to 4 sentence summary for each narrative.
  3. Provide 5 to 10 example posts (include user, short caption excerpt, and URL) that reflect each narrative.

  Here are the posts:
  {formatted}
  """
    return prompt

  # === Summarize with GPT ===
  def summarize_chunk(prompt):
    response = client.chat.completions.create(
      model=OPENAI_MODEL,
      messages=[
        {"role": "system", "content": "You are a skilled narrative analyst for social media."},
        {"role": "user", "content": prompt}
      ],
      temperature=0.4 # Keeps output factual and consistent
    )
    return response.choices[0].message.content # Extracts assistant's response

  # === Process all chunks ===
  all_summaries = []

  for chunk in chunk_posts(posts, CHUNK_SIZE):
    prompt = format_prompt(chunk)
    print("Summarizing a chunk of", len(chunk), "posts...")
    summary = summarize_chunk(prompt)
    all_summaries.append(summary)

  # === Save output ===
  with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    for i, summary in enumerate(all_summaries):
      f.write(f"\n\n## Summary Chunk {i+1}\n\n")
      f.write(summary)
  
  print(f"✅ Narrative summaries saved to {OUTPUT_FILE}")
  
  return all_summaries

if __name__ == "__main__":
  generate_chunked_summaries()
