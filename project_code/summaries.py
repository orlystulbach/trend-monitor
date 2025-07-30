import openai
import pandas as pd

client = openai.OpenAI()

with open("output/gpt_narrative_summary_2.md", "r", encoding="utf-8") as f:
  all_chunks_text = f.read()

def synthesize_final_narratives(summaries_text):
  final_prompt = f"""
You are a social media analyst specializing in narrative research. You are given a combined collection of narrative summaries and post excerpts that reflect conversations about Gaza from Instagram captions. The summaries were originally generated in smaller batches, but your task is to treat them as one unified dataset.

Your goals are:

1. **Identify and name each distinct narrative** or theme expressed across the entire dataset.
2. For each narrative:
   - Write a clear and concise **summary** (2 to 4 sentences) that captures the core idea, tone, and emotional resonance.
   - Select **2 to 3 example posts** that best illustrate the narrative, choosing from the references included in the original text.
3. **Avoid duplication** — merge overlapping or semantically similar narratives into one.
4. Ensure the output is **structured and readable**, suitable for inclusion in a research report.

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

final_output = synthesize_final_narratives(all_chunks_text)

with open("output/final_narratives_2.md", "w", encoding="utf-8") as f:
    f.write(final_output)

print("✅ Final narrative synthesis saved to output/final_narratives.md")