import streamlit as st
from project_code.forum_scout import run_ingestion
from project_code.fetch_insta_captions import enrich_instagram_captions
from project_code.caption_cleaning import clean_captions_file
from project_code.summarize_chunks import generate_chunked_summaries
from project_code.summaries import synthesize_final_narratives

st.title("Instagram Trend Analyzer")

st.markdown("Enter keywords you'd like to search on Instagram via ForumScout:")
user_input = st.text_area("Keywords (comma-separated)")

# Step 1: Scrape data

if st.button("🧲 Scrape Posts"):
    keywords = [kw.strip() for kw in user_input.split(",") if kw.strip()]
    endpoints = {
        "instagram": "instagram_search"
        # Later: add checkboxes for Reddit, YouTube, etc.
    }

    col1, col2, col3 = st.columns(3)

    with col1:
        st.info("Scraping posts...")
        run_ingestion(keywords=keywords, endpoints=endpoints)
        st.success("Done scraping posts!")

        with open("output/forumscout_data.csv") as f:
            st.download_button("📄 Download Data CSV", f, file_name="forumscout_data.csv")
    
    input_file_data = "output/forumscout_data.csv"
    output_file_data = "output/forumscout_data_with_captions.csv"
    
    with col2: 
        st.info("Scraping captions...")
        try:
            enrich_instagram_captions(input_file_data, output_file_data)
            st.success("Done scraping captions!")
            
            with open(output_file_data, "rb") as f:
                st.download_button("📄 Download Captions CSV", f, file_name="forumscout_data_with_captions.csv")
        except Exception as e:
            st.error(f"Error: {e}")
    
    input_file_clean = "output/forumscout_data_with_captions.csv"
    output_file_clean = "output/forumscout_cleaned_data.csv"

    with col3: 
        st.info("Cleaning captions...")
        try:
            clean_captions_file(input_file=input_file_clean, output_file=output_file_clean, st=st)
            st.success(f"Done cleaning captions!")

            with open(output_file_clean, "rb") as f:
                st.download_button("📄 Download Cleaned CSV", f, file_name="forumscout_cleaned_data.csv")

        except Exception as e:
            st.error(f"Error cleaning captions: {e}")

# Step 3: Generate chunked summaries
# if st.button("🧠 Generate GPT Summaries"):
    
    summaries = []

    with st.spinner("Generating summaries from Instagram captions..."):
        summaries = generate_chunked_summaries()
    
    st.success("Chunked summaries saved!")

    if len(summaries) > 1:
        for i, summary in enumerate(summaries, start=1):
            st.markdown(f"### Chunk Summary {i}")
            st.text_area("", summary, height=300)
    else:
        for i, summary in enumerate(summaries, start=1):
            st.markdown(f"### Chunk Summary")
            st.text_area("", summary, height=300)
    
    with open(output_file_clean, "rb") as f:
        st.download_button("📄 Download Chunk Summaries", f, file_name="output/gpt_narrative_summary.md")

# if st.button("🧩 Synthesize Final Narratives"):
    try:
        all_chunks_text = []

        with open("output/gpt_narrative_summary.md", "r", encoding="utf-8") as f:
            all_chunks_text = f.read()

        with st.spinner("Analyzing summaries and generating final narratives..."):
            final_output = synthesize_final_narratives(all_chunks_text)
        
        with open("output/final_narratives.md", "w", encoding="utf-8") as f:
            f.write(final_output)

        st.success("Final synthesis complete!")
        st.download_button("📄 Download Final Narrative Summary", final_output, file_name="output/final_narratives.md")

        st.markdown("### 📝 Final Narrative Output")
        st.markdown(final_output)
        # display_final_narratives(final_output)

    except FileNotFoundError:
        st.error("❌ 'gpt_narrative_summary.md' not found. Run the chunk summarization step first.")
    except Exception as e:
        st.error(f"Unexpected error: {e}")

# Step 4: Merge into unified narrative
# if st.button("📚 Compile Final Narrative List"):
#     final_text = narrative_unifier.synthesize_final_narrative("output/gpt_narrative_summary.md")
#     st.text_area("📋 Final Narrative Summary", final_text, height=500)
