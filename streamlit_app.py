import streamlit as st
from project_code.forum_scout_multiple import run_ingestion
from project_code.fetch_captions import enrich_captions
from project_code.caption_cleaning import clean_captions_file
from project_code.summarize_chunks import generate_chunked_summaries
from project_code.summaries import synthesize_final_narratives
from utils.logger import log_to_browser
import os
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

RAW_CSV = OUTPUT_DIR / "forumscout_data.csv"
TIKTOK_CSV = OUTPUT_DIR / "tiktok_data.csv"
CAPTIONS_CSV = OUTPUT_DIR / "forumscout_data_with_captions.csv"
CLEAN_CSV = OUTPUT_DIR / "forumscout_cleaned_data.csv"
CHUNKS_MD = OUTPUT_DIR / "gpt_narrative_summary.md"
FINAL_MD = OUTPUT_DIR / "final_narratives.md"

# Initialize session state
if 'analysis_complete' not in st.session_state:
    st.session_state.analysis_complete = False
if 'scraping_complete' not in st.session_state:
    st.session_state.scraping_complete = False
if 'captions_complete' not in st.session_state:
    st.session_state.captions_complete = False
if 'cleaning_complete' not in st.session_state:
    st.session_state.cleaning_complete = False
if 'summaries' not in st.session_state:
    st.session_state.summaries = []
if 'final_narratives' not in st.session_state:
    st.session_state.final_narratives = ""
if 'selected_platforms' not in st.session_state:
    st.session_state.selected_platforms = []
if 'sort_by_recent' not in st.session_state:
    st.session_state.sort_by = False
if 'recency' not in st.session_state:
    st.session_state.recency = False

st.set_page_config(
    page_title="Narrative Analysis Tool",
    page_icon="📱",
    layout="wide"
)

st.title("📱 Narrative Analysis Tool")
st.markdown("Enter keywords you'd like to search:")
user_input = st.text_area("Keywords (comma-separated)")


platform_options = {
    "Instagram": "instagram_search",
    "YouTube": "youtube_search",
    "Reddit Posts": "reddit_posts_search",
    "Reddit Comments": "reddit_comments_search",
    "TikTok": 'tiktok',
    "Twitter": "x_search",
}

st.markdown("Select platforms you'd like to explore. I would advise choosing **one** platform at a time for the best data.")
selected_platforms = st.multiselect(
    "Select platform(s)",
    list(platform_options.keys()),
)

if any(platform in selected_platforms for platform in ["Instagram", "TikTok", "Reddit Posts", "Reddit Comments"]):
    st.session_state.sort_by = True
else:
    st.session_state.sort_by = False

if any(platform in selected_platforms for platform in ["YouTube"]):
    st.session_state.recency = True
else:
    st.session_state.recency = False

if any(platform in selected_platforms for platform in ["Twitter"]):
    st.badge("Twitter will not return the user but you can click on the provided URL to find their handle.", color="blue")


selected_sort = None
if st.session_state.sort_by:
    selected_sort = st.selectbox(
        "What would you like to sort by?",
        ("Latest", "Most Popular"),
        index=None,
        placeholder="Selected sort method..."
    )

recency_selection = None
if st.session_state.recency:
    recency_display = {
        0: "last hour",
        1: "today",
        2: "this week",
        3: "this month",
        4: "this year"
    }
    recency_values = {
        0: "last_hour",
        1: "today",
        2: "this_week", 
        3: "this_month",
        4: "this_year"
    }
    selection = st.segmented_control(
        "Recency of Posts",
        options=recency_display.keys(),
        format_func=lambda option: recency_display[option],
        selection_mode="single",
    )
    if selection is not None:
        recency_selection = recency_values[selection]

chunk_count = 1

# Step 1: Scrape data
if st.button("🧲 Scrape Posts"):
    keywords = [kw.strip() for kw in user_input.split(",") if kw.strip()]
    
    # log_to_browser(f"Scraping {keywords} from {selected_platforms}")

    if not keywords:
        st.warning("Please enter at least one keyword.")
    elif not selected_platforms:
        st.warning("Please select at least one platform.")
    else:
        # Dynamically build endpoints based on user selection
        endpoints = {
            platform.lower().replace(" ", "_"): platform_options[platform]
            for platform in selected_platforms
        }
    
        print(f"Scraping {keywords} from {endpoints.keys()}")
        # log_to_browser(f"Scraping {keywords} from {endpoints.keys()}")

        progress_bar = st.progress(0)
        # status_text = st.empty()

        col1, col2, col3 = st.columns(3)

        with col1:
            # st.info("Scraping posts...")
            status_box_1 = st.empty()
            status_box_1.text("Scraping posts...")
            # status_text.text("Scraping posts...")
            try: 
                print(str(RAW_CSV))
                run_ingestion(keywords=keywords, endpoints=endpoints, sort_by=selected_sort, recency=recency_selection, output_file=str(RAW_CSV))
                st.session_state.scraping_complete = True
                progress_bar.progress(33)
                status_box_1.success("Done scraping posts!")
            except Exception as e:
                st.error(f"Error: {e}")

        with col2: 
            # st.info("Scraping captions...")
            # status_text.text("Scraping captions...")
            status_box_2 = st.empty()
            status_box_2.text("Scraping captions...")
            try:
                input_file_data = str(RAW_CSV)
                output_file_data = str(CAPTIONS_CSV)
                enrich_captions(input_file_data, output_file_data)
                st.session_state.captions_complete = True
                progress_bar.progress(66)
                status_box_2.success("Done scraping captions!")
            except Exception as e:
                st.error(f"Error: {e}")
            
        with col3: 
            # st.info("Cleaning captions...")
            # status_text.text("Cleaning captions...")
            status_box_3 = st.empty()
            status_box_3.text("Cleaning captions...")
            try:
                input_file_clean = str(CAPTIONS_CSV)
                output_file_clean = str(CLEAN_CSV)
                clean_captions_file(input_file=input_file_clean, output_file=output_file_clean, st=st)
                st.session_state.cleaning_complete = True
                progress_bar.progress(100)
                status_box_3.success(f"Done cleaning captions!")
            except Exception as e:
                st.error(f"Error cleaning captions: {e}")
                    
            # st.success("Scraping complete.")

col1, col2, col3 = st.columns(3)

# Show download buttons and results if scraping is complete
if st.session_state.scraping_complete:
    # st.subheader("📥 Download Data Files")
    with col1:
        if RAW_CSV.exists():
            with RAW_CSV.open("rb") as f:
                st.download_button(
                    label="📄 Download Raw Data CSV", 
                    data=f.read(),
                    file_name=RAW_CSV.name,
                    key="download_raw_data"
                )
        else:
            st.warning("Raw data file not found")

if st.session_state.captions_complete:
    with col2:
        if CAPTIONS_CSV.exists():
            with CAPTIONS_CSV.open("rb") as f:
                st.download_button(
                    label="📄 Download Captions CSV", 
                    data=f.read(),
                    file_name=CAPTIONS_CSV.name,
                    key="download_captions_data"
                )
        else:
            st.warning("Captions file not found")

if st.session_state.cleaning_complete:
    with col3:
        if CLEAN_CSV.exists():
            with CLEAN_CSV.open("rb") as f:
                st.download_button(
                    label="📄 Download Cleaned CSV", 
                    data=f.read(),
                    file_name=CLEAN_CSV.name,
                    key="download_cleaned_data"
                )
        else:
            st.warning("Cleaned data file not found")

if st.button("💡 Generate Summaries"):
    # Generate summaries
    with st.spinner("Generating summaries from content..."):
        try: 
            summaries = generate_chunked_summaries()
            chunk_count = len(summaries)
            st.session_state.summaries = summaries
            st.success("Chunked summaries generated!")
        except Exception as e:
            st.error(f"Error generating summaries by chunk: {e}. Check https://platform.openai.com/settings/organization/billing/overview to ensure we have enough in our OpenAI API billing.")
    
    # Show summaries if available
    if st.session_state.summaries:
        st.subheader("🧠 Generated Summaries")
        
        if chunk_count > 1:
            for i, summary in enumerate(st.session_state.summaries, start=1):
                st.markdown(f"### Chunk Summary {i}")
                st.text_area("", summary, height=300, key=f"summary_{i}")
        else:
            for i, summary in enumerate(st.session_state.summaries, start=1):
                st.markdown(f"### Chunk Summary")
                st.text_area("", summary, height=300, key=f"summary_{i}")
        
        if CHUNKS_MD.exists():
            with CHUNKS_MD.open("rb") as f:
                st.download_button(
                    label="📄 Download Chunk Summaries", 
                    data=f.read(),
                    file_name=CHUNKS_MD.name,
                    key="download_summaries"
                )
        else:
            st.warning("Summary file not found")

        # Generate final narratives
        if CHUNKS_MD.exists():
            all_chunks_text = CHUNKS_MD.read_text(encoding="utf-8")
            # with open("output/gpt_narrative_summary.md", "r", encoding="utf-8") as f:
            #     all_chunks_text = f.read()

            with st.spinner("Analyzing summaries and generating final narratives..."):
                try: 
                    final_output = synthesize_final_narratives(all_chunks_text)
                    st.session_state.final_narratives = final_output
                    st.session_state.analysis_complete = True
                    st.success("Analysis complete!")
                except Exception as e:
                    st.error(f"Error generating final narratives: {e}. Check https://platform.openai.com/settings/organization/billing/overview to ensure we have enough in our OpenAI API billing.")
            
            FINAL_MD.write_text(final_output, encoding="utf-8")
            # with open("output/final_narratives.md", "w", encoding="utf-8") as f:
            #     f.write(final_output)

        else:
            st.error("❌ 'gpt_narrative_summary.md' not found. Run the chunk summarization step first.")
        # except Exception as e:
            st.error(f"Unexpected error: {e}")

# Show final narratives if analysis is complete
if st.session_state.analysis_complete:
    st.subheader("📝 Final Narrative Analysis")
    
    st.download_button(
        label="📄 Download Final Narratives", 
        data=st.session_state.final_narratives,
        file_name=FINAL_MD.name,
        key="download_final_narratives"
    )

    st.markdown("### 🎯 Discovered Narratives")
    st.markdown(st.session_state.final_narratives)

# Reset button to start over
if st.session_state.analysis_complete or st.session_state.scraping_complete:
    if st.button("🔄 Start New Analysis"):
        # Reset all session state
        st.session_state.analysis_complete = False
        st.session_state.scraping_complete = False
        st.session_state.captions_complete = False
        st.session_state.cleaning_complete = False
        st.session_state.summaries = []
        st.session_state.final_narratives = ""
        st.rerun()