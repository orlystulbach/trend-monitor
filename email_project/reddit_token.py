# Run this LOCALLY (not in GitHub Actions).
# pip install praw

import os
import webbrowser
from urllib.parse import urlparse, parse_qs
from http.server import HTTPServer, BaseHTTPRequestHandler
import praw

CLIENT_ID = os.getenv("REDDIT_CLIENT_ID") or "YOUR_CLIENT_ID"
CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET") or "YOUR_CLIENT_SECRET"
USER_AGENT = "trend-monitor:trend-monitoring:0.1 (by /u/your_reddit_username)"
REDIRECT_URI = "http://localhost:8080"  # must match the app setting on reddit.com/prefs/apps
SCOPES = ["identity", "read"]            # add more if you need them

# Simple local HTTP server to catch the redirect and grab ?code=...
class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        qs = parse_qs(urlparse(self.path).query)
        code = qs.get("code", [None])[0]
        if code:
            self.server.auth_code = code
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"You can close this tab. Auth code received.")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Missing 'code' parameter.")
    def log_message(self, *args, **kwargs):
        return  # keep console clean

def main():
    reddit = praw.Reddit(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        user_agent=USER_AGENT,
    )

    auth_url = reddit.auth.url(
        scopes=SCOPES,
        state="state123",
        duration="permanent",  # <-- ensures you'll get a refresh token
    )
    print("Opening browser to authorize:", auth_url)
    webbrowser.open(auth_url)

    # Start local server to receive the redirect with ?code=...
    with HTTPServer(("localhost", 8080), _Handler) as httpd:
        print("Waiting for redirect at http://localhost:8080 ...")
        httpd.handle_request()
        code = getattr(httpd, "auth_code", None)

    if not code:
        raise SystemExit("No authorization code received. Try again.")

    refresh_token = reddit.auth.authorize(code)
    print("\n✅ REFRESH TOKEN:\n", refresh_token)
    print("\nSave this in GitHub Secrets as REDDIT_REFRESH_TOKEN")

if __name__ == "__main__":
    main()
