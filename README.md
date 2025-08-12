### Trend Monitoring by Keyword

Input keyword into the Streamlit web interface and choose which platform(s) to search for how that keyword has been trending.

Uses API Keys provided by ForumScout for Instagram, YouTube, and Reddit (posts and comments)

Uses Apify's TikTok Scraper to scrape TikTok for the keyword.

Uses OpenAI API Key to discover narratives and organize them, providing titles, summaries, and sample excerpts and posts.

## Process of Events
1. Fetch the data from each social media platform.
2. If necessary, fetch the actual content using third-party tools.
3. Clean all of the data.
4. Summarize by chunks of 30 posts into different narratives.
5. Summarize those summarized chunks into distinct narratives.