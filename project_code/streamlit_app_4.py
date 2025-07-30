import streamlit as st
import pandas as pd
import requests
import time
import csv
import os
import re
from datetime import datetime, timezone
import instaloader
from tqdm import tqdm
import openai
import io
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Page config
st.set_page_config(
    page_title="Instagram Narrative Analysis Tool",
    page_icon="📱",
    layout="wide"
)

# Initialize session state
if 'analysis_complete' not in st.session_state:
    st.session_state.analysis_complete = False
if 'final_narratives' not in st.session_state:
    st.session_state.final_narratives = ""

# Title and description
st.title("📱 Instagram Narrative Analysis Tool")
st.markdown("Analyze how keywords are being discussed on Instagram with AI-powered narrative extraction")

# Get API keys from environment or Streamlit secrets
try:
    # Try Streamlit secrets first (for cloud deployment)
    forumscout_key = st.secrets.get("FORUMSCOUT_API_KEY") or os.getenv("FORUMSCOUT_API_KEY")
    openai_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
except:
    # Fallback to environment variables (for local development)
    forumscout_key = os.getenv("FORUMSCOUT_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

# Sidebar for configuration
with st.sidebar:
    st.header("🔧 Configuration")
    
    # API Keys status
    st.subheader("🔑 API Keys Status")
    if forumscout_key:
        st.success("✅ ForumScout API Key loaded")
    else:
        st.error("❌ ForumScout API Key missing")
    
    if openai_key:
        st.success("✅ OpenAI API Key loaded")
    else:
        st.error("❌ OpenAI API Key missing")
    
    # Keywords input
    st.subheader("Keywords to Analyze")
    keywords_input = st.text_area(
        "Keywords (one per line)",
        value="children starving in gaza\nzionism\njews",
        height=100,
        help="Enter keywords you want to track on Instagram"
    )
    
    # Analysis settings
    st.subheader("Analysis Settings")
    sort_by = st.selectbox("Sort posts by", ["top", "recent"])
    chunk_size = st.slider("Posts per AI analysis chunk", 10, 50, 30)
    
    # Run button
    run_analysis = st.button("🚀 Start Analysis", type="primary", 
                           disabled=not (forumscout_key and openai_key))

# Helper functions (your existing code adapted)
def fetch_forumscout_data(api_key, keyword, sort_by):
    """Fetch Instagram URLs from ForumScout"""
    url = "https://forumscout.app/api/instagram_search"
    headers = {"X-API-Key": api_key}
    params = {"keyword": keyword, "sort_by": sort_by}
    
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Error fetching {keyword}: {response.status_code}")
        return []

def extract_shortcode(url):
    """Extract Instagram shortcode from URL"""
    match = re.search(r"/p/([A-Za-z0-9_-]+)", url)
    return match.group(1) if match else None

def fetch_caption(shortcode, loader, max_retries=3):
    """Fetch caption using instaloader with retry logic"""
    for attempt in range(max_retries):
        try:
            post = instaloader.Post.from_shortcode(loader.context, shortcode)
            return post.caption or ""
        except instaloader.exceptions.LoginRequiredException:
            st.warning("⚠️ Instagram login may be required for some posts")
            return ""
        except instaloader.exceptions.QueryReturnedForbiddenException:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            else:
                return ""
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            else:
                return ""
    return ""

def clean_caption(text):
    """Clean caption text"""
    if not isinstance(text, str):
        return ""
    text = re.sub(r"[^\w\s#@]", "", text.lower())
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def chunk_posts(posts, size):
    """Split posts into chunks"""
    for i in range(0, len(posts), size):
        yield posts[i:i + size]

def format_prompt(post_chunk):
    """Format posts for GPT analysis"""
    formatted = "\n".join([
        f"- @{p['author']}: \"{p['cleaned_caption'].strip()}\" ({p['url']})"
        for p in post_chunk if p['cleaned_caption'].strip()
    ])
    
    prompt = f"""
You are a social media analyst reviewing Instagram captions about various topics.
Your job is to:
1. Identify and name distinct narratives or conversation themes.
2. Write a 2 to 4 sentence summary for each narrative.
3. Provide 3 to 5 example posts (include short caption excerpt and URL) that reflect each narrative.

Here are the posts:
{formatted}
"""
    return prompt

def summarize_chunk(client, prompt):
    """Summarize a chunk of posts with GPT"""
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a skilled narrative analyst for social media."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.4
    )
    return response.choices[0].message.content

def synthesize_final_narratives(client, summaries_text):
    """Create final narrative synthesis"""
    final_prompt = f"""
You are a social media analyst specializing in narrative research. You are given a combined collection of narrative summaries and post excerpts from Instagram captions. 

Your goals are:
1. **Identify and name each distinct narrative** or theme expressed across the entire dataset.
2. For each narrative:
   - Write a clear and concise **summary** (2 to 4 sentences) that captures the core idea, tone, and emotional resonance.
   - Select **3 to 5 example posts** that best illustrate the narrative (including excerpt from the caption and URL).
3. **Avoid duplication** — merge overlapping or semantically similar narratives into one.
4. Ensure the output is **structured and readable**.

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

# Main analysis logic
if run_analysis:
    if not forumscout_key or not openai_key:
        st.error("Please provide both API keys to continue.")
        st.stop()
    
    # Parse keywords
    keywords = [k.strip() for k in keywords_input.strip().split('\n') if k.strip()]
    
    if not keywords:
        st.error("Please enter at least one keyword.")
        st.stop()
    
    # Initialize clients with better configuration
    openai_client = openai.OpenAI(api_key=openai_key)
    
    # Configure instaloader to be less aggressive
    loader = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        compress_json=False
    )
    
    st.success(f"Starting analysis for {len(keywords)} keywords...")
    
    # Progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    all_records = []
    
    # Step 1: Fetch URLs from ForumScout
    status_text.text("🔍 Fetching Instagram URLs...")
    for i, keyword in enumerate(keywords):
        status_text.text(f"🔍 Fetching URLs for: {keyword}")
        posts = fetch_forumscout_data(forumscout_key, keyword, sort_by)
        
        for post in posts:
            record = {
                "platform": "instagram",
                "keyword": keyword,
                "content": post.get("text", ""),
                "author": post.get("username", ""),
                "timestamp": post.get("date", datetime.now(timezone.utc).isoformat()),
                "url": post.get("url", "")
            }
            all_records.append(record)
        
        progress_bar.progress((i + 1) / (len(keywords) * 4))  # 25% per major step
        time.sleep(1)  # Rate limiting
    
    st.info(f"Found {len(all_records)} Instagram posts")
    
    # Step 2: Fetch captions with better error handling
    status_text.text("📝 Fetching Instagram captions...")
    caption_progress = st.progress(0)
    
    successful_fetches = 0
    failed_fetches = 0
    
    for i, record in enumerate(all_records):
        if record["url"]:
            shortcode = extract_shortcode(record["url"])
            if shortcode:
                caption = fetch_caption(shortcode, loader)
                record["caption"] = caption
                if caption:
                    successful_fetches += 1
                else:
                    failed_fetches += 1
            else:
                record["caption"] = ""
                failed_fetches += 1
        else:
            record["caption"] = ""
            failed_fetches += 1
        
        caption_progress.progress((i + 1) / len(all_records))
        
        # Update main progress (25-50%)
        progress_bar.progress(0.25 + 0.25 * (i + 1) / len(all_records))
        
        # Add delay to avoid rate limiting
        if i % 10 == 0 and i > 0:  # Every 10 requests
            time.sleep(2)
    
    st.info(f"Successfully fetched {successful_fetches} captions, {failed_fetches} failed")
    
    # Step 3: Clean captions
    status_text.text("🧹 Cleaning captions...")
    df = pd.DataFrame(all_records)
    df["cleaned_caption"] = df["caption"].fillna("").apply(clean_caption)
    
    # Filter out empty captions
    df_clean = df[df["cleaned_caption"].str.strip() != ""]
    posts_for_analysis = df_clean[["cleaned_caption", "author", "url"]].to_dict(orient="records")
    
    progress_bar.progress(0.5)
    st.info(f"Cleaned {len(posts_for_analysis)} posts with valid captions")
    
    # Step 4: AI Analysis
    status_text.text("🤖 Analyzing narratives with AI...")
    all_summaries = []
    
    chunks = list(chunk_posts(posts_for_analysis, chunk_size))
    
    for i, chunk in enumerate(chunks):
        status_text.text(f"🤖 Analyzing chunk {i+1}/{len(chunks)} ({len(chunk)} posts)...")
        prompt = format_prompt(chunk)
        summary = summarize_chunk(openai_client, prompt)
        all_summaries.append(summary)
        
        # Update progress (50-75%)
        progress_bar.progress(0.5 + 0.25 * (i + 1) / len(chunks))
    
    # Step 5: Final synthesis
    status_text.text("🔗 Synthesizing final narratives...")
    combined_summaries = "\n\n".join([f"## Summary Chunk {i+1}\n\n{summary}" 
                                     for i, summary in enumerate(all_summaries)])
    
    final_narratives = synthesize_final_narratives(openai_client, combined_summaries)
    
    progress_bar.progress(1.0)
    status_text.text("✅ Analysis complete!")
    
    # Store results in session state
    st.session_state.analysis_complete = True
    st.session_state.final_narratives = final_narratives
    st.session_state.df_results = df_clean
    st.session_state.keywords_analyzed = keywords

# Display results
if st.session_state.analysis_complete:
    st.header("📊 Analysis Results")
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    df_results = st.session_state.df_results
    
    col1.metric("Total Posts", len(df_results))
    col2.metric("Keywords", len(st.session_state.keywords_analyzed))
    col3.metric("With Captions", len(df_results[df_results["cleaned_caption"] != ""]))
    col4.metric("Unique Authors", df_results["author"].nunique())
    
    # Final Narratives with Enhanced Examples
    st.subheader("🎯 Discovered Narratives")
    
    # Display the original narratives
    narratives_text = st.session_state.final_narratives
    st.markdown(narratives_text)
    
    # # Extract and display the example posts mentioned in the narratives
    # st.subheader("📱 Posts Referenced in Analysis")
    # st.markdown("*These are the specific Instagram posts that were used as examples in the narrative analysis above.*")
    
    # df_results = st.session_state.df_results
    
    # # Find all post examples mentioned in the narratives
    # import re
    
    # # Look for patterns like: @username: "caption excerpt" or @username - "caption"
    # patterns = [
    #     r'@(\w+):\s*["""]([^"""]+)["""]',  # @user: "caption"
    #     r'@(\w+)\s*-\s*["""]([^"""]+)["""]',  # @user - "caption"
    #     r'@(\w+):\s*"([^"]+)"',  # @user: "caption"
    #     r'@(\w+)\s*-\s*"([^"]+)"'  # @user - "caption"
    # ]
    
    # example_posts = []
    # found_examples = set()  # To avoid duplicates
    
    # for pattern in patterns:
    #     matches = re.findall(pattern, narratives_text, re.IGNORECASE)
    #     for username, caption_excerpt in matches:
    #         # Skip if we already found this example
    #         key = f"{username.lower()}:{caption_excerpt[:30]}"
    #         if key in found_examples:
    #             continue
    #         found_examples.add(key)
            
    #         # Find the matching post in our data
    #         matching_posts = df_results[
    #             df_results['author'].str.lower() == username.lower()
    #         ]
            
    #         # If multiple posts from same user, try to find the one with matching content
    #         if len(matching_posts) > 1:
    #             content_matches = matching_posts[
    #                 matching_posts['caption'].str.contains(caption_excerpt[:20], case=False, na=False) |
    #                 matching_posts['cleaned_caption'].str.contains(caption_excerpt[:20], case=False, na=False)
    #             ]
    #             if not content_matches.empty:
    #                 matching_posts = content_matches
            
    #         if not matching_posts.empty:
    #             post = matching_posts.iloc[0]
    #             example_posts.append(post)
    
    # # Display the example posts
    # if example_posts:
    #     for i, post in enumerate(example_posts, 1):
    #         st.markdown(f"**Example {i}:**")
            
    #         # User handle
    #         st.markdown(f"**User:** @{post['author']}")
            
    #         # Caption
    #         caption = post['caption'] if pd.notna(post['caption']) else post['content']
    #         if caption:
    #             st.markdown(f"**Caption:** {caption}")
    #         else:
    #             st.markdown("**Caption:** *No caption available*")
            
    #         # URL
    #         if post['url']:
    #             st.markdown(f"**URL:** {post['url']}")
    #         else:
    #             st.markdown("**URL:** *No URL available*")
            
    #         st.markdown("---")
    
    # else:
    #     st.info("No specific post examples were found in the narrative text.")
        
    #     # Fallback: show some sample posts from the analysis
    #     st.markdown("**Sample posts from the analysis:**")
    #     sample_posts = df_results[df_results['caption'].str.len() > 20].head(3)
        
    #     for i, (idx, post) in enumerate(sample_posts.iterrows(), 1):
    #         st.markdown(f"**Sample {i}:**")
    #         st.markdown(f"**User:** @{post['author']}")
            
    #         caption = post['caption'] if pd.notna(post['caption']) else post['content']
    #         if caption:
    #             st.markdown(f"**Caption:** {caption}")
    #         else:
    #             st.markdown("**Caption:** *No caption available*")
            
    #         if post['url']:
    #             st.markdown(f"**URL:** {post['url']}")
    #         else:
    #             st.markdown("**URL:** *No URL available*")
            
    #         st.markdown("---")
    
    # Raw data view
    with st.expander("📋 View Raw Data"):
        st.dataframe(df_results)
    
    # Download buttons
    col1, col2 = st.columns(2)
    
    with col1:
        csv_data = df_results.to_csv(index=False)
        st.download_button(
            label="📥 Download Data (CSV)",
            data=csv_data,
            file_name=f"instagram_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    with col2:
        st.download_button(
            label="📄 Download Narratives (MD)",
            data=st.session_state.final_narratives,
            file_name=f"narratives_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown"
        )

# Instructions
else:
    st.info("""
    ### 🚀 How to use this tool:
    
    1. **Get API Keys**:
       - [ForumScout API Key](https://forumscout.app/developers) - for finding Instagram posts
       - [OpenAI API Key](https://platform.openai.com/api-keys) - for narrative analysis
    
    2. **Enter Keywords**: Add the topics you want to analyze (one per line)
    
    3. **Configure Settings**: Choose sorting method and analysis chunk size
    
    4. **Run Analysis**: Click "Start Analysis" and wait for results
    
    5. **View Results**: Explore discovered narratives and download data
    
    ### 📊 What this tool does:
    - Finds Instagram posts related to your keywords
    - Downloads the actual post captions
    - Uses AI to identify conversation themes and narratives
    - Provides structured analysis with examples
    
    ### ⚠️ Important Notes:
    - Instagram may block requests if too many are made quickly
    - Some posts may be private or require login to access
    - Rate limiting is built-in to avoid getting blocked
    - If you get 403 errors, try again later or use fewer keywords
    """)

# Footer
st.markdown("---")
st.markdown("Built with ❤️ using Streamlit | Powered by ForumScout + OpenAI")