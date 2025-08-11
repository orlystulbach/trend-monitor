import os, ssl, smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from report import build_report

def _env_list(name, default=""):
    raw = os.environ.get(name, default)
    return [x.strip() for x in raw.split(",") if x.strip()]

def main():
    # Inputs come from environment (can be tuned in Actions)
    keywords = _env_list("REPORT_KEYWORDS", "")     # e.g., "israel, campus protest"
    platforms = _env_list("REPORT_PLATFORMS", "TikTok")
    sort_by = os.environ.get("REPORT_SORT_BY")      # "Latest" | "Most Popular" | None
    recency = os.environ.get("REPORT_RECENCY")      # "last_hour"|"today"|"this_week"|"this_month"|"this_year"|None

    html, attachments = build_report(
        keywords=keywords,
        selected_platforms=platforms,
        sort_by=sort_by,
        recency=recency,
        attach_files=True,
    )

    from_addr = os.environ["GMAIL_USERNAME"]
    to_addrs  = _env_list("MAIL_TO")               # comma-separated
    subject   = os.environ.get("MAIL_SUBJECT", "Weekly Narrative Report")

    msg = MIMEMultipart()
    msg["From"] = from_addr
    msg["To"] = ", ".join(to_addrs)
    msg["Subject"] = subject
    msg.attach(MIMEText(html, "html"))

    for filename, content in attachments:
        part = MIMEApplication(content)
        part.add_header("Content-Disposition", "attachment", filename=filename)
        msg.attach(part)

    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx) as s:
        s.login(os.environ["GMAIL_USERNAME"], os.environ["GMAIL_APP_PASSWORD"])
        s.sendmail(from_addr, to_addrs, msg.as_string())

if __name__ == "__main__":
    main()
