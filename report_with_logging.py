import os
from datetime import datetime
from project_code.forum_scout_multiple import run_ingestion
from project_code.fetch_captions import enrich_captions
from project_code.caption_cleaning import clean_captions_file
from project_code.summarize_chunks import generate_chunked_summaries
from project_code.summaries import synthesize_final_narratives
import traceback
# --- logging setup ---
import logging, os, sys, traceback
from logging.handlers import RotatingFileHandler
from pathlib import Path
import pandas as pd  # already used below

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
LOG_PATH = OUTPUT_DIR / "weekly_report.log"

def _make_logger():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("weekly_report")
    logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
    logger.propagate = False  # don’t double-log

    # Clear old handlers if re-imported
    logger.handlers = []

    # Console for GitHub Actions
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
    ch.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s", "%Y-%m-%d %H:%M:%S"))
    logger.addHandler(ch)

    # File (rotating)
    fh = RotatingFileHandler(LOG_PATH, maxBytes=2_000_000, backupCount=2, encoding="utf-8")
    fh.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
    fh.setFormatter(logging.Formatter("%(asctime)s\t%(levelname)s\t%(name)s\t%(message)s"))
    logger.addHandler(fh)

    # Optional: HTTP debug (requests/urllib3)
    if os.getenv("HTTP_DEBUG", "0") == "1":
        for name in ("urllib3", "requests"):
            http_logger = logging.getLogger(name)
            http_logger.setLevel(logging.DEBUG)
            http_logger.propagate = True
        logger.info("HTTP_DEBUG enabled for requests/urllib3")

    return logger

logger = _make_logger()
# --- end logging setup ---

RAW_CSV = OUTPUT_DIR / "forumscout_data.csv"
CAPTIONS_CSV = OUTPUT_DIR / "forumscout_data_with_captions.csv"
CLEAN_CSV = OUTPUT_DIR / "forumscout_cleaned_data.csv"
CHUNKS_MD = OUTPUT_DIR / "gpt_narrative_summary.md"
FINAL_MD = OUTPUT_DIR / "final_narratives.md"

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
        return html, []

    endpoints = {
        p.lower().replace(" ", "_"): PLATFORM_OPTIONS[p]
        for p in selected_platforms if p in PLATFORM_OPTIONS
    }
    logger.info("Resolved endpoints: %s", endpoints)

    # 1) Ingest
    try:
        logger.info("Step 1: run_ingestion started")
        run_ingestion(keywords=keywords, endpoints=endpoints, sort_by=sort_by, recency=recency)
        logger.info("Step 1: run_ingestion finished")
    except Exception as e:
        logger.exception("Error during ingestion")
        RAW_CSV.write_text(f"error during ingestion: {e}")
    _ = _df_summary(RAW_CSV, "Raw CSV")

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
    _ = _df_summary(CAPTIONS_CSV, "Captions CSV")

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
    _ = _df_summary(CLEAN_CSV, "Cleaned CSV")

    # 4) Chunked summaries
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

    # Build diagnostics and HTML (same as before, but log row counts already handled)
    raw_info = _df_summary(RAW_CSV, "Raw CSV")
    cap_info = _df_summary(CAPTIONS_CSV, "Captions CSV")
    clean_info = _df_summary(CLEAN_CSV, "Cleaned CSV")

    final_output_html = FINAL_MD.read_text(encoding="utf-8").replace("\n", "<br>")
    logger.info("=== Weekly report run end ===")

    # ... construct `html` as you had it, then:
    attachments = []
    if attach_files:
        for filename, path in [
            ("forumscout_data.csv", RAW_CSV),
            ("forumscout_data_with_captions.csv", CAPTIONS_CSV),
            ("forumscout_cleaned_data.csv", CLEAN_CSV),
            ("gpt_narrative_summary.md", CHUNKS_MD),
            ("final_narratives.md", FINAL_MD),
            ("weekly_report.log", LOG_PATH),  # 👈 attach the log
        ]:
            if path.exists():
                attachments.append((filename, path.read_bytes()))

    return html, attachments
