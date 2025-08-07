import openai
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

client = openai.OpenAI()

# all_chunks_text = ''

# with open("../output/gpt_narrative_summary.md", "r", encoding="utf-8") as f:
#   all_chunks_text = f.read()

def synthesize_final_narratives(summaries_text):
  final_prompt = f"""
You are a social media analyst specializing in narrative research. You are given a combined collection of narrative summaries and post excerpts that reflect conversations about Gaza from Instagram captions. The summaries were originally generated in smaller batches, but your task is to treat them as one unified dataset.

Your goals are:

1. **Identify and name each distinct narrative** or theme expressed across the entire dataset.
2. For each narrative:
   - Write a clear and concise **summary** (2 to 4 sentences) that captures the core idea, tone, and emotional resonance.
   - Select **5 to 10 example posts** that best illustrate the narrative, choosing from the references included in the original text. ALWAYS MAKE SURE TO INCLUDE the user, a short caption excerpt, a title excerpt where accessible, and the URL (very important to include the URL)!
3. **Avoid duplication** — merge overlapping or semantically similar narratives into one.
4. Ensure the output is **structured and readable**, suitable for inclusion in a research report. Please make sure the Narrative Title is bolded, the summary is on a new line, and the examples are on new lines.

This is the structure I want:
Narrative #: Title
Summary: Summary
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