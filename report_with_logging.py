# report.py
from datetime import datetime
from pathlib import Path
import logging, os, sys, traceback
from logging.handlers import RotatingFileHandler
import pandas as pd

from project_code.forum_scout_multiple import run_ingestion
from email_project.email_fetch_captions import enrich_captions
from project_code.caption_cleaning import clean_captions_file
from project_code.summarize_chunks import generate_chunked_summaries
from project_code.summaries import synthesize_final_narratives

# -------- logging setup --------
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
LOG_PATH = OUTPUT_DIR / "weekly_report.log"

def _make_logger():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_PATH.touch(exist_ok=True)

    logger = logging.getLogger("weekly_report")
    logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
    logger.propagate = False
    logger.handlers = []

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logger.level)
    ch.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s", "%Y-%m-%d %H:%M:%S"))
    logger.addHandler(ch)

    fh = RotatingFileHandler(LOG_PATH, maxBytes=2_000_000, backupCount=2, encoding="utf-8")
    fh.setLevel(logger.level)
    fh.setFormatter(logging.Formatter("%(asctime)s\t%(levelname)s\t%(name)s\t%(message)s"))
    logger.addHandler(fh)

    if os.getenv("HTTP_DEBUG", "0") == "1":
        for name in ("urllib3", "requests"):
            http_logger = logging.getLogger(name)
            http_logger.setLevel(logging.DEBUG)
            http_logger.propagate = True
        logger.info("HTTP_DEBUG enabled for requests/urllib3")

    logger.info("Logger initialized. Writing to %s", LOG_PATH)
    return logger

logger = _make_logger()
# -------- end logging setup --------

RAW_CSV = OUTPUT_DIR / "forumscout_data.csv"
CAPTIONS_CSV = OUTPUT_DIR / "forumscout_data_with_captions.csv"
CLEAN_CSV = OUTPUT_DIR / "forumscout_cleaned_data.csv"
CHUNKS_MD = OUTPUT_DIR / "gpt_narrative_summary.md"
FINAL_MD = OUTPUT_DIR / "final_narratives.md"

# Map UI names to ingestion endpoints (ensure these match your ingestion code)
PLATFORM_OPTIONS = {
    "Instagram": "instagram_search",
    "YouTube": "youtube_search",
    "Reddit Posts": "reddit_posts_search",
    "Reddit Comments": "reddit_comments_search",
    "TikTok": "tiktok",
    "Twitter": "x_search",
}

def _df_summary(path: Path, name: str):
    if not path.exists():
        logger.warning("%s not found at %s", name, path)
        return f"❌ {name}: file not found"
    try:
        df = pd.read_csv(path)
    except Exception as e:
        logger.exception("Failed reading %s at %s", name, path)
        return f"❌ {name}: failed to read CSV ({e})"
    if df.empty:
        logger.warning("%s is empty at %s", name, path)
        return f"⚠️ {name}: 0 rows"
    logger.info("%s loaded: %d rows, %d cols", name, len(df), len(df.columns))
    return f"✅ {name}: {len(df):,} rows, {len(df.columns)} cols"

def _df_head_html(path: Path, max_rows=5):
    if not path.exists():
        return ""
    try:
        df = pd.read_csv(path)
        if df.empty:
            return "<em>(no rows)</em>"
        return df.head(max_rows).to_html(index=False, border=0)
    except Exception:
        return "<em>(unable to render preview)</em>"

def _collect_attachments():
    files = [
        ("forumscout_data.csv", RAW_CSV),
        ("forumscout_data_with_captions.csv", CAPTIONS_CSV),
        ("forumscout_cleaned_data.csv", CLEAN_CSV),
        ("gpt_narrative_summary.md", CHUNKS_MD),
        ("final_narratives.md", FINAL_MD),
        ("weekly_report.log", LOG_PATH),
    ]
    out = []
    for name, path in files:
        if path.exists():
            out.append((name, path.read_bytes()))    
    return out

def build_report(keywords, selected_platforms, sort_by=None, recency=None, attach_files=True):
    logger.info("=== Weekly report run start ===")
    logger.info("Inputs | keywords=%s | platforms=%s | sort_by=%s | recency=%s",
                keywords, selected_platforms, sort_by, recency)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Normalize inputs
    keywords = [kw.strip() for kw in (keywords or []) if kw.strip()]
    selected_platforms = [p.strip() for p in (selected_platforms or []) if p.strip()]

    problems = []
    if not keywords:
        problems.append("No keywords provided.")
    if not selected_platforms:
        problems.append("No platforms selected.")
    missing = [p for p in selected_platforms if p not in PLATFORM_OPTIONS]
    if missing:
        problems.append(f"Unknown platforms: {', '.join(missing)}")
    if problems:
        logger.error("Input problems: %s", problems)
        html = "<h3>Input problems</h3><ul>" + "".join(f"<li>{p}</li>" for p in problems) + "</ul>"
        logging.shutdown()
        return html, []

    endpoints = {p.lower().replace(" ", "_"): PLATFORM_OPTIONS[p] for p in selected_platforms}
    logger.info("Resolved endpoints: %s", endpoints)

    # 1) Ingest
    try:
        logger.info("Step 1: run_ingestion started")
        run_ingestion(keywords=keywords, endpoints=endpoints, sort_by='Latest', recency=recency)
        logger.info("Step 1: run_ingestion finished")
    except Exception as e:
        logger.exception("Error during ingestion")
        RAW_CSV.write_text(f"error during ingestion: {e}")
    raw_info = _df_summary(RAW_CSV, "Raw CSV")

    # 2) Captions
    try:
        logger.info("Step 2: enrich_captions started")
        if RAW_CSV.exists():
            enrich_captions(str(RAW_CSV), str(CAPTIONS_CSV))
            logger.info("Step 2: enrich_captions finished")
        else:
            logger.warning("Step 2 skipped: Raw CSV not found")
    except Exception:
        logger.exception("Error during caption enrichment")
        CAPTIONS_CSV.write_text("error during caption fetch")
    cap_info = _df_summary(CAPTIONS_CSV, "Captions CSV")

    # 3) Clean
    class _NullSt:
        def __getattr__(self, _): return lambda *a, **k: None
    try:
        logger.info("Step 3: clean_captions_file started")
        if CAPTIONS_CSV.exists():
            clean_captions_file(input_file=str(CAPTIONS_CSV), output_file=str(CLEAN_CSV), st=_NullSt())
            logger.info("Step 3: clean_captions_file finished")
        else:
            logger.warning("Step 3 skipped: Captions CSV not found")
    except Exception:
        logger.exception("Error during cleaning")
        CLEAN_CSV.write_text("error during cleaning")

    clean_info = _df_summary(CLEAN_CSV, "Cleaned CSV")
    skip_openai = False

    if "⚠️" in clean_info or "❌" in clean_info:
      skip_openai = True
    else:
        try:
            df_clean = pd.read_csv(CLEAN_CSV)
            if "cleaned_caption" not in df_clean.columns:
                logger.warning("'cleaned_caption' column missing — skipping OpenAI steps")
                skip_openai = True
            elif df_clean["cleaned_caption"].dropna().eq("").all():
                logger.warning("'cleaned_caption' column is empty — skipping OpenAI steps")
                skip_openai = True
        except Exception as e:
            logger.exception("Failed to read cleaned CSV for caption check")
            skip_openai = True

    # 4) Chunked summaries
    if skip_openai:
      logger.warning("Cleaned CSV empty or missing — skipping OpenAI steps")
      final_output = "[Skipped — no data to summarize]"
      FINAL_MD.write_text(final_output, encoding="utf-8")
      return "<p>No data to summarize this week.</p>", _collect_attachments()
    else:
      try:
          logger.info("Step 4: generate_chunked_summaries started")
          summaries = generate_chunked_summaries()
          with open(CHUNKS_MD, "w", encoding="utf-8") as f:
              for s in summaries:
                  f.write(s.strip() + "\n\n---\n\n")
          logger.info("Step 4: generate_chunked_summaries finished | chunks=%d", len(summaries))
      except Exception:
          logger.exception("Error generating chunked summaries")
          with open(CHUNKS_MD, "w", encoding="utf-8") as f:
              f.write("[No summaries generated due to error]\n")

      # 5) Final narratives
      try:
          logger.info("Step 5: synthesize_final_narratives started")
          all_chunks_text = CHUNKS_MD.read_text(encoding="utf-8")
          final_output = synthesize_final_narratives(all_chunks_text)
          FINAL_MD.write_text(final_output, encoding="utf-8")
          logger.info("Step 5: synthesize_final_narratives finished | final chars=%d", len(final_output))
      except Exception:
          logger.exception("Error generating final narratives")
          final_output = "[No final narrative generated due to error]"
          FINAL_MD.write_text(final_output, encoding="utf-8")

    # Build HTML
    meta_html = "<br>".join([
        f"<b>Keywords:</b> {', '.join(keywords)}",
        f"<b>Platforms:</b> {', '.join(selected_platforms)}",
        f"<b>Sort by:</b> {sort_by or 'None'}",
        f"<b>Recency:</b> {recency or 'None'}",
        f"<b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}",
    ])
    raw_preview = _df_head_html(RAW_CSV)
    cap_preview = _df_head_html(CAPTIONS_CSV)
    clean_preview = _df_head_html(CLEAN_CSV)
    final_output_html = FINAL_MD.read_text(encoding="utf-8").replace("\n", "<br>")

    html = f"""
    <div style="font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;">
      <h2>Weekly Narrative Report</h2>
      <p>{meta_html}</p>
      <h3>Data health</h3>
      <ul>
        <li>{raw_info}</li>
        <li>{cap_info}</li>
        <li>{clean_info}</li>
      </ul>
      <h3>Raw sample</h3>
      {raw_preview}
      <h3>Captions sample</h3>
      {cap_preview}
      <h3>Cleaned sample</h3>
      {clean_preview}
      <h3>Final Narrative Analysis</h3>
      <div style="white-space:pre-wrap; border:1px solid #eee; padding:12px; border-radius:8px; background:#fafafa;">
        {final_output_html}
      </div>
    </div>
    """

    logger.info("=== Weekly report run end ===")
    # ensure file handlers flush for artifact/attachment
    logging.shutdown()

    # Attachments
    # attachments = []
    # if attach_files:
    #     for filename, path in [
    #         ("forumscout_data.csv", RAW_CSV),
    #         ("forumscout_data_with_captions.csv", CAPTIONS_CSV),
    #         ("forumscout_cleaned_data.csv", CLEAN_CSV),
    #         ("gpt_narrative_summary.md", CHUNKS_MD),
    #         ("final_narratives.md", FINAL_MD),
    #         ("weekly_report.log", LOG_PATH),
    #     ]:
    #         if path.exists():
    #             attachments.append((filename, path.read_bytes()))

    attachments = _collect_attachments()
    return html, attachments
