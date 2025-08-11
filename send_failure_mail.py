# send_failure_mail.py
import os, ssl, smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def main():
    from_addr = os.environ["GMAIL_USERNAME"]
    to_addrs  = [x.strip() for x in os.environ["MAIL_TO"].split(",") if x.strip()]
    subject   = os.environ.get("MAIL_SUBJECT", "Weekly Report") + " — FAILED"

    # GitHub context (for quick link to logs)
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    run_url = f"https://github.com/{repo}/actions/runs/{run_id}" if repo and run_id else "(no run url)"

    html = f"""
    <div style="font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;">
      <h2>Weekly Report: ❌ Failed</h2>
      <p>The scheduled job failed. Check logs here:<br>
      <a href="{run_url}">{run_url}</a></p>
      <p>If this is an OpenAI billing issue, add funds (here: https://platform.openai.com/settings/organization/billing/overview) or fix quota, then re-run the workflow.</p>
    </div>
    """

    msg = MIMEMultipart()
    msg["From"] = from_addr
    msg["To"] = ", ".join(to_addrs)
    msg["Subject"] = subject
    msg.attach(MIMEText(html, "html"))

    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx) as s:
        s.login(os.environ["GMAIL_USERNAME"], os.environ["GMAIL_APP_PASSWORD"])
        s.sendmail(from_addr, to_addrs, msg.as_string())

if __name__ == "__main__":
    main()
