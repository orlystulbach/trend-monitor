import openai
import pandas as pd
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

client = openai.OpenAI()

BASE_DIR = Path(__file__).resolve().parent.parent  # go up to project root
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
FINAL_MD = OUTPUT_DIR / "final_narratives.md"

# all_chunks_text = ''

# with open("../output/gpt_narrative_summary.md", "r", encoding="utf-8") as f:
#   all_chunks_text = f.read()

def synthesize_final_narratives(summaries_text):
  final_prompt = f"""
You are a social media analyst specializing in narrative research. You are given a combined collection of narrative summaries and post excerpts about Gaza from Instagram captions. These summaries were originally generated in smaller batches, but you must treat them as one unified dataset.

Your task:

Identify and name exactly 3 distinct narratives by merging semantically similar or overlapping narratives from the dataset. Clearly explain each narrative's essence.

When merging narratives:

Combine only if they share core subject matter, emotional tone, and perspective.

Keep all example posts from the merged narratives (do not drop or rewrite them, except to remove exact duplicates).

For each narrative:

Write a summary (2 to 4 sentences) that clearly conveys the key idea, emotional tone, and perspective.

Provide 5 to 6 example posts that best illustrate the narrative.

For each example, preserve the username, exact short excerpt of caption, and URL exactly as given. Do not change wording, punctuation, or spelling.

Output must follow this structure exactly:
This is the structure I want:
Narrative #: **Title**  
Summary: [2–4 sentence summary]
Examples:
1. @user: "<short caption excerpt>" (<URL>)
2. @user: "<short caption excerpt>" (<URL>)
3. @user: "<short caption excerpt>" (<URL>)
4. @user: "<short caption excerpt>" (<URL>)
5. @user: "<short caption excerpt>" (<URL>)

Focus on understanding patterns, emotions, and frames of thought expressed by the public.

Here is the full combined content:
\"\"\"
{summaries_text}
\"\"\"
"""
  response = client.chat.completions.create(
      model="gpt-4",
      messages=[
          {"role": "system", "content": "You are a social media narrative analyst."},
          {"role": "user", "content": final_prompt}
      ],
      temperature=0.4
  )
  return response.choices[0].message.content

# if __name__ == "__main__":
#   final_output = synthesize_final_narratives(all_chunks_text)

#   with open("../output/final_narratives_2.md", "w", encoding="utf-8") as f:
#       f.write(final_output)

#   print("✅ Final narrative synthesis saved to output/final_narratives.md")