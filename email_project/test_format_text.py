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
    lines = [f"{title}", "Narratives"]
    for idx, n in enumerate(final_json.get("narratives", []), start=1):
        name = (n.get("name") or f"Narrative {idx}").strip()
        summary = (n.get("summary") or "").strip()
        lines.append(f"# Narrative {idx}: {name}")
        if summary:
            lines.append(f"Summary: {summary}")
        lines.append("")
        lines.append("Examples:")
        for ex in (n.get("examples", [])[:10]):
            handle = (ex.get("handle") or "@unknown").strip() or "@unknown"
            excerpt = str(ex.get("excerpt", "")).strip().replace("\n", " ")
            url = (ex.get("url") or "").strip()
            lines.append(f'- {handle}: "{excerpt}" ({url})')
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"

# quick test (use your sample JSON)
print(_render_markdown("reddit_comments", {
    "narratives": [{
        "name": "Humanitarian Crisis in Gaza",
        "summary": "The ongoing conflict has led to severe humanitarian issues in Gaza, with reports of famine and displacement affecting the civilian population. Many voices are calling for urgent action to alleviate the suffering of those trapped in the conflict.",
        "examples": [
            {"handle":"@unknown","excerpt":"gaza is being starved now is the time to act the un has stated that every part of gaza is in famine conditions","url":"https://www.reddit.com/r/WorldNewsHeadlines/comments/1mq9mwe/israeli_forces_brutally_assault_palestinian/n8pgsk9/"},
            {"handle":"@unknown","excerpt":"many of the people being held by israel are children who havent been charged with any crime not murders","url":"https://www.reddit.com/r/World_Now/comments/1mpvefn/nowhere_in_the_post_or_banner_does_it_mention/n8pguui/"},
            {"handle":"@unknown","excerpt":"the ongoing methodical murder and displacement of an entire ethnic group certainly is","url":"https://www.reddit.com/r/soccer/comments/1mq8v08/palestine_football_association_announces_that_2/n8pgtxl/"},
            {"handle":"@unknown","excerpt":"please do this please respond if you dont you approve it with your silence never again is now the hate is out of control","url":"https://www.reddit.com/r/Jewish/comments/1mo8b8a/what_would_you_do_with_a_comment_like_this/n8nn9o1/"},
            {"handle":"@unknown","excerpt":"there is no ethnic cleansing or genocide that is another lie being perpetuated by hamas and pushed by iranian propaganda","url":"https://www.reddit.com/r/RedditNoReservations/comments/1mohgna/un_will_add_hamas_to_blacklist_of_groups_that/n8nn2pl/"},
        ]
    }]}
))
