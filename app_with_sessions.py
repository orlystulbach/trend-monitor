import streamlit as st
from project_code.forum_scout_multiple import run_ingestion
from project_code.fetch_captions import enrich_captions
from project_code.caption_cleaning import clean_captions_file
from project_code.summarize_chunks import generate_chunked_summaries
from project_code.summaries import synthesize_final_narratives
from utils.logger import log_to_browser
import os

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

selected_platforms = st.multiselect(
    "Which platforms would you like to explore?",
    list(platform_options.keys())
)

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

        # with col1:
        #     st.markdown("### 🧲 Step 1: Scrape Posts")
        # with col2:
        #     st.markdown("### 📝 Step 2: Get Captions") 
        # with col3:
        #     st.markdown("### 🧹 Step 3: Clean Data")
        
        # st.markdown("---")

        # progress_bar = st.progress(0)
        # status_text = st.empty()

        with col1:
            # st.info("Scraping posts...")
            status_box_1 = st.empty()
            status_box_1.text("Scraping posts...")
            # status_text.text("Scraping posts...")
            try: 
                run_ingestion(keywords=keywords, endpoints=endpoints)
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
                input_file_data = "output/forumscout_data.csv"
                output_file_data = "output/forumscout_data_with_captions.csv"
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
                input_file_clean = "output/forumscout_data_with_captions.csv"
                output_file_clean = "output/forumscout_cleaned_data.csv"
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
        try:
            with open("output/forumscout_data.csv", "rb") as f:
                st.download_button(
                    label="📄 Download Raw Data CSV", 
                    data=f.read(),
                    file_name="forumscout_data.csv",
                    key="download_raw_data"
                )
        except FileNotFoundError:
            st.warning("Raw data file not found")

if st.session_state.captions_complete:
    with col2:
        try:
            with open("output/forumscout_data_with_captions.csv", "rb") as f:
                st.download_button(
                    label="📄 Download Captions CSV", 
                    data=f.read(),
                    file_name="forumscout_data_with_captions.csv",
                    key="download_captions_data"
                )
        except FileNotFoundError:
            st.warning("Captions file not found")

if st.session_state.cleaning_complete:
    with col3:
        try:
            with open("output/forumscout_cleaned_data.csv", "rb") as f:
                st.download_button(
                    label="📄 Download Cleaned CSV", 
                    data=f.read(),
                    file_name="forumscout_cleaned_data.csv",
                    key="download_cleaned_data"
                )
        except FileNotFoundError:
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
            st.error(f"Error generating summaries by chunk: {e}")
    
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
        
        try:
            with open("output/gpt_narrative_summary.md", "rb") as f:
                st.download_button(
                    label="📄 Download Chunk Summaries", 
                    data=f.read(),
                    file_name="gpt_narrative_summary.md",
                    key="download_summaries"
                )
        except FileNotFoundError:
            st.warning("Summary file not found")

        # Generate final narratives
        try:
            all_chunks_text = ''
            with open("output/gpt_narrative_summary.md", "r", encoding="utf-8") as f:
                all_chunks_text = f.read()

            with st.spinner("Analyzing summaries and generating final narratives..."):
                final_output = synthesize_final_narratives(all_chunks_text)
                st.session_state.final_narratives = final_output
            
            with open("output/final_narratives.md", "w", encoding="utf-8") as f:
                f.write(final_output)

            st.session_state.analysis_complete = True
            st.success("Analysis complete!")

        except FileNotFoundError:
            st.error("❌ 'gpt_narrative_summary.md' not found. Run the chunk summarization step first.")
        except Exception as e:
            st.error(f"Unexpected error: {e}")

# Show final narratives if analysis is complete
if st.session_state.analysis_complete:
    st.subheader("📝 Final Narrative Analysis")
    
    st.download_button(
        label="📄 Download Final Narratives", 
        data=st.session_state.final_narratives,
        file_name="final_narratives.md",
        key="download_final_narratives"
    )

    st.markdown("### 🎯 Discovered Narratives")
    st.markdown(st.session_state.final_narratives)

    # Extract and display example posts (same logic as before)
    # st.subheader("📱 Posts Referenced in Analysis")
    # st.markdown("*These are the specific Instagram posts that were used as examples in the narrative analysis above.*")
    
    # try:
    #     import pandas as pd
    #     import re
        
    #     # Load the cleaned data to find example posts
    #     df_results = pd.read_csv("output/forumscout_cleaned_data.csv")
    #     narratives_text = st.session_state.final_narratives
        
    #     # Find all post examples mentioned in the narratives
    #     patterns = [
    #         r'@(\w+):\s*["""]([^"""]+)["""]',  # @user: "caption"
    #         r'@(\w+)\s*-\s*["""]([^"""]+)["""]',  # @user - "caption"
    #         r'@(\w+):\s*"([^"]+)"',  # @user: "caption"
    #         r'@(\w+)\s*-\s*"([^"]+)"'  # @user - "caption"
    #     ]
        
    #     example_posts = []
    #     found_examples = set()  # To avoid duplicates
        
    #     for pattern in patterns:
    #         matches = re.findall(pattern, narratives_text, re.IGNORECASE)
    #         for username, caption_excerpt in matches:
    #             # Skip if we already found this example
    #             key = f"{username.lower()}:{caption_excerpt[:30]}"
    #             if key in found_examples:
    #                 continue
    #             found_examples.add(key)
                
    #             # Find the matching post in our data
    #             matching_posts = df_results[
    #                 df_results['author'].str.lower() == username.lower()
    #             ]
                
    #             # If multiple posts from same user, try to find the one with matching content
    #             if len(matching_posts) > 1:
    #                 content_matches = matching_posts[
    #                     matching_posts['caption'].str.contains(caption_excerpt[:20], case=False, na=False) |
    #                     matching_posts['cleaned_caption'].str.contains(caption_excerpt[:20], case=False, na=False)
    #                 ]
    #                 if not content_matches.empty:
    #                     matching_posts = content_matches
                
    #             if not matching_posts.empty:
    #                 post = matching_posts.iloc[0]
    #                 example_posts.append(post)
        
    #     # Display the example posts
    #     if example_posts:
    #         for i, post in enumerate(example_posts, 1):
    #             st.markdown(f"**Example {i}:**")
                
    #             # User handle
    #             st.markdown(f"**User:** @{post['author']}")
                
    #             # Caption
    #             caption = post['caption'] if pd.notna(post['caption']) else post['content']
    #             if caption:
    #                 st.markdown(f"**Caption:** {caption}")
    #             else:
    #                 st.markdown("**Caption:** *No caption available*")
                
    #             # URL
    #             if post['url']:
    #                 st.markdown(f"**URL:** {post['url']}")
    #             else:
    #                 st.markdown("**URL:** *No URL available*")
                
    #             st.markdown("---")
        
    #     else:
    #         st.info("No specific post examples were found in the narrative text.")
            
    #         # Fallback: show some sample posts from the analysis
    #         st.markdown("**Sample posts from the analysis:**")
    #         sample_posts = df_results[df_results['caption'].str.len() > 20].head(3)
            
    #         for i, (idx, post) in enumerate(sample_posts.iterrows(), 1):
    #             st.markdown(f"**Sample {i}:**")
    #             st.markdown(f"**User:** @{post['author']}")
                
    #             caption = post['caption'] if pd.notna(post['caption']) else post['content']
    #             if caption:
    #                 st.markdown(f"**Caption:** {caption}")
    #             else:
    #                 st.markdown("**Caption:** *No caption available*")
                
    #             if post['url']:
    #                 st.markdown(f"**URL:** {post['url']}")
    #             else:
    #                 st.markdown("**URL:** *No URL available*")
                
    #             st.markdown("---")
    
    # except Exception as e:
    #     st.error(f"Error displaying example posts: {e}")

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