import os
import re
import json
import openai
import pandas as pd
from dotenv import load_dotenv
from pathlib import Path
from typing import List, Dict, Any

# Load environment variables
load_dotenv()
client = openai.OpenAI()

BASE_DIR   = Path(__file__).resolve().parent.parent  # go up to project root
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CLEAN_CSV = OUTPUT_DIR / "forumscout_cleaned_data.csv"
CHUNKS_MD = OUTPUT_DIR / "gpt_narrative_summary.md"

# ---------- Helpers ----------
def _infer_platform_from_url(u: str) -> str:
    u = (u or "").lower()
    if "instagram.com" in u: return "instagram"
    if "tiktok.com"    in u: return "tiktok"
    if "x.com" in u or "twitter.com" in u: return "twitter"
    if "reddit.com"    in u: return "reddit"
    if "youtube.com" in u or "youtu.be" in u: return "youtube"
    return "unknown"

def _fmt_post(p: Dict[str, Any]) -> str:
    cap = str(p["cleaned_caption"]).strip().replace("\n", " ")
    if len(cap) > 280:
        cap = cap[:277] + "..."
    author = (p.get("author") or "").strip() or "unknown"
    url = (p.get("url") or "").strip()
    return f'- @{author}: "{cap}" ({url})'

def _extract_json(text: str) -> Dict[str, Any]:
    """Parse model output into JSON; supports raw JSON or ```json blocks."""
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"```json\s*(\{.*?\})\s*```", text, flags=re.S)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    m = re.search(r"(\{(?:[^{}]|(?1))*\})", text, flags=re.S)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    raise ValueError("Could not parse JSON from model output")

def _platform_display_name(p: str) -> str:
    m = {
        "instagram": "Instagram",
        "tiktok": "TikTok",
        "twitter": "Twitter",
        "x": "Twitter",
        "x_search": "Twitter",
        "reddit": "Reddit",
        "reddit_posts": "Reddit Posts",
        "reddit_comments": "Reddit Comments",
        "youtube": "YouTube",
    }
    p = (p or "").strip().lower()
    return m.get(p, p.replace("_", " ").title())

def _render_markdown(platform_name: str, final_json: dict) -> str:
    title = _platform_display_name(platform_name)
    lines = [f"{title}", "Narratives"]  # plain lines (no markdown ##)

    narratives = final_json.get("narratives", [])
    for idx, n in enumerate(narratives, start=1):
        name = (n.get("name") or f"Narrative {idx}").strip()
        summary = (n.get("summary") or "").strip()

        # Header exactly as requested
        lines.append(f"# Narrative {idx}: {name}")
        if summary:
            lines.append(f"Summary: {summary}")
        lines.append("")  # blank line before Examples label

        lines.append("Examples:")
        examples = n.get("examples", [])[:10]  # cap to 10 examples
        for ex in examples:
            handle = (ex.get("handle") or "@unknown").strip() or "@unknown"
            excerpt = str(ex.get("excerpt", "")).strip().replace("\n", " ")
            url = (ex.get("url") or "").strip()
            # keep quotes and URL formatting as in your sample
            lines.append(f'- {handle}: "{excerpt}" ({url})')

        # blank line between narratives
        lines.append("")

    # trailing newline for file friendliness
    return "\n".join(lines).rstrip() + "\n"

def _gpt_chunk(platform_name: str, posts_chunk: List[Dict[str, Any]], model: str, temp: float) -> Dict[str, Any]:
    formatted = "\n".join(_fmt_post(p) for p in posts_chunk)
    prompt = f"""
You are analyzing posts from **{platform_name}** about humanitarian and political issues in Gaza.
From ONLY the posts below, produce **2–3 candidate narratives** in **compact JSON** with this exact schema:

{{
  "narratives": [
    {{
      "name": "short descriptive title",
      "summary": "2–4 sentence summary",
      "examples": [
        {{"handle":"@user","excerpt":"10–25 word excerpt","url":"https://..."}},
        ...
      ]
    }},
    ...
  ]
}}

Rules:
- Choose **2 or 3** narratives max.
- Provide **5–10 examples per narrative** (each must include @handle, short excerpt, and URL).
- If a Twitter/X example has author "unknown", try to infer the @handle from the URL or text.
- Output **only** valid JSON. No commentary.

Posts:
{formatted}
"""
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You output only valid JSON that matches the requested schema."},
            {"role": "user", "content": prompt},
        ],
        temperature=temp
    )
    return _extract_json(resp.choices[0].message.content)

def _gpt_merge(platform_name: str, json_a: Dict[str, Any], json_b: Dict[str, Any], model: str, temp: float) -> Dict[str, Any]:
    prompt = f"""
You are consolidating narratives for **{platform_name}**.

You will be given two JSON payloads, each with 2–3 narratives and examples from different batches of posts. 
Merge them into a single set of **2–3** narratives total (not per input), each with a **2–4 sentence summary** and **5–10 total examples** (handles, short excerpt, URL). 
- Merge similar narratives; rename for clarity if needed.
- Keep example diversity across inputs.
- Output **only** valid JSON with the same schema as before.

JSON A:
{json.dumps(json_a, ensure_ascii=False)}

JSON B:
{json.dumps(json_b, ensure_ascii=False)}
"""
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You output only valid JSON that matches the requested schema."},
            {"role": "user", "content": prompt},
        ],
        temperature=temp
    )
    return _extract_json(resp.choices[0].message.content)

# ---------- Main ----------
def generate_chunked_summaries(
    INPUT_FILE: str = str(CLEAN_CSV),
    OUTPUT_FILE: str = str(CHUNKS_MD),
    OPENAI_MODEL: str = "gpt-4o-mini",
    SPLIT_THRESHOLD: int = 30,      # if platform has >30 posts, split into two halves
    TEMPERATURE: float = 0.3
):
    # Load data
    df = pd.read_csv(INPUT_FILE)

    # Basic hygiene
    if "cleaned_caption" not in df.columns:
        raise ValueError("Expected column 'cleaned_caption' in the input CSV.")
    df = df[df["cleaned_caption"].notnull() & df["cleaned_caption"].astype(str).str.strip().ne("")]
    if df.empty:
        Path(OUTPUT_FILE).write_text("No posts to summarize.\n", encoding="utf-8")
        print("⚠️ No posts found after cleaning.")
        return []

    # Ensure platform
    if "platform" not in df.columns:
        df["platform"] = df.get("url", "").apply(_infer_platform_from_url)

    cols = ["cleaned_caption", "author", "url"]

    # ensure columns exist
    for c in cols:
        if c not in df.columns:
            df[c] = ""

    # make them true strings and remove NaNs/<NA>
    df[cols] = df[cols].astype("string").fillna("")

    all_sections = []
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        # Process one platform at a time
        for platform_name, grp in df.groupby("platform", sort=False):
            posts = grp[["cleaned_caption", "author", "url"]].to_dict(orient="records")
            n = len(posts)
            if n == 0:
                continue

            print(f"{platform_name}: {n} post(s).", flush=True)

            # --- Split logic: only if > SPLIT_THRESHOLD, split into two halves; else one chunk
            if n > SPLIT_THRESHOLD:
                mid = (n + 1) // 2  # first half gets the extra if odd
                chunk_a = posts[:mid]
                chunk_b = posts[mid:]
                cand_a = _gpt_chunk(platform_name, chunk_a, OPENAI_MODEL, TEMPERATURE)
                cand_b = _gpt_chunk(platform_name, chunk_b, OPENAI_MODEL, TEMPERATURE)
                final_json = _gpt_merge(platform_name, cand_a, cand_b, OPENAI_MODEL, TEMPERATURE)
            else:
                final_json = _gpt_chunk(platform_name, posts, OPENAI_MODEL, TEMPERATURE)

            section_md = _render_markdown(platform_name, final_json or {"narratives": []})
            # Ensure separation between sections
            if f.tell() > 0:
                f.write("\n\n")
            f.write(section_md)
            all_sections.append(section_md)

    print(f"✅ Platform-based narrative summaries saved to {OUTPUT_FILE}")
    return all_sections

if __name__ == "__main__":
    generate_chunked_summaries()
