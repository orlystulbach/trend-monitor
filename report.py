import os
from datetime import datetime
from project_code.forum_scout_multiple import run_ingestion
from project_code.fetch_captions import enrich_captions
from project_code.caption_cleaning import clean_captions_file
from project_code.summarize_chunks import generate_chunked_summaries
from project_code.summaries import synthesize_final_narratives
import traceback

OUTPUT_DIR = "output"
RAW_CSV = os.path.join(OUTPUT_DIR, "forumscout_data.csv")
CAPTIONS_CSV = os.path.join(OUTPUT_DIR, "forumscout_data_with_captions.csv")
CLEAN_CSV = os.path.join(OUTPUT_DIR, "forumscout_cleaned_data.csv")
CHUNKS_MD = os.path.join(OUTPUT_DIR, "gpt_narrative_summary.md")
FINAL_MD = os.path.join(OUTPUT_DIR, "final_narratives.md")

PLATFORM_OPTIONS = {
  "Instagram": "instagram_search",
  "YouTube": "youtube_search",
  "Reddit Posts": "reddit_posts_search",
  "Reddit Comments": "reddit_comments_search",
  "TikTok": "tiktok",
  "Twitter": "x_search",
}

def build_report(
    keywords,
    selected_platforms,
    sort_by=None, # "Latest" | "Most Popular" | None
    recency=None, # "last_hour" | "today" | "this_week" | "this_month" | "this_year" | None - for YouTube
    attach_files=True
):
  """
  Runs the full pipeline headlessly and returns (html, attachments).
  attachments = list of (filename, bytes)
  """
  os.makedirs(OUTPUT_DIR, exist_ok=True)

  # Build endpoints, like in Streamlit code
  endpoints = {
    platform.lower().replace(" ", "_"): PLATFORM_OPTIONS[platform]
    for platform in selected_platforms
    if platform in PLATFORM_OPTIONS
  }

  # 1) Ingest
  run_ingestion(
    keywords=[kw.strip() for kw in keywords if kw.strip()],
    endpoints=endpoints,
    sort_by=sort_by,
    recency=recency,
  )

  # 2) Captions
  enrich_captions(RAW_CSV, CAPTIONS_CSV)

  # 3) Clean
  # Provide dummy 'st'-like object so your cleaner can call st.* safely if it expects it
  class _NullSt:
    def __getattr__(self, _):
      return lambda *a, **k: None
  clean_captions_file(input_file=CAPTIONS_CSV, output_file=CLEAN_CSV, st=_NullSt())

  # 4) Chunked summaries
  try:
    summaries = generate_chunked_summaries()
    with open(CHUNKS_MD, "w", encoding="utf-8") as f:
      for s in summaries:
        f.write(s.strip() + "\n\n--\n\n")
  except Exception as e:
    error_msg = f"Error generating chunked summaries: {e}. Check https://platform.openai.com/settings/organization/billing/overview to ensure we have enough in our OpenAI API billing."
    print(error_msg)
    traceback.print_exc()
    summaries = []
    # Create placeholder file so later steps don't fail
    with open(CHUNKS_MD, "w", encoding="utf-8") as f:
      f.write(f"[No summaries generated due to error: {e}]\n")
  
  # 5) Final narratives
  try:
    with open(CHUNKS_MD, "r", encoding="utf-8") as f:
      all_chunks_text = f.read()
    final_output = synthesize_final_narratives(all_chunks_text)
    with open(FINAL_MD, "w", encoding="utf-8") as f:
      f.write(final_output)
  except Exception as e:
    error_msg = f"Error generating final narratives: {e}"
    print(error_msg)
    traceback.print_exc()
    final_output = f"[No final narrative generated due to error: {e}]"
    with open(FINAL_MD, "w", encoding="utf-8") as f:
        f.write(final_output)

  # Build HTML email body (simple, readable)
  now = datetime.now().strftime("%Y-%m-%d %H:%M")
  kw_str = ", ".join(keywords)
  plats_str = ", ".join(selected_platforms) or "None"
  meta_lines = [
    f"<b>Keywords:</b> {kw_str or 'None'}",
    f"<b>Platforms:</b> {plats_str}",
    f"<b>Sort by:</b> {sort_by or 'None'}",
    f"<b>Recency:</b> {recency or 'None'}",
    f"<b>Generated:</b> {now}",
  ]
  meta_html = "<br>".join(meta_lines)

  final_output_html = final_output.replace("\n", "<br>")

  html = f"""
    <div style="font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;">
      <h2>Weekly Narrative Report</h2>
      <p>{meta_html}</p>
      <h3>Final Narrative Analysis</h3>
      <div style="white-space:pre-wrap; border:1px solid #eee; padding:12px; border-radius:8px; background:#fafafa;">
        {final_output_html}
      </div>
      <p style="margin-top:16px;">Attachments include raw, captions, cleaned CSVs, and chunk summaries (MD), if enabled.</p>
    </div>
    """
  
  attachments = []
  if attach_files:
    def _read_bytes(path):
      try:
          with open(path, "rb") as f:
              return f.read()
      except FileNotFoundError:
          return None

    for filename, path in [
      ("forumscout_data.csv", RAW_CSV),
      ("forumscout_data_with_captions.csv", CAPTIONS_CSV),
      ("forumscout_cleaned_data.csv", CLEAN_CSV),
      ("gpt_narrative_summary.md", CHUNKS_MD),
      ("final_narratives.md", FINAL_MD),
    ]:
      b = _read_bytes(path)
      if b is not None:
        attachments.append((filename, b))

  return html, attachments