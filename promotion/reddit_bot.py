import os, json, time, random, sys
from datetime import datetime

REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
REDDIT_USERNAME = os.getenv("REDDIT_USERNAME", "")
REDDIT_PASSWORD = os.getenv("REDDIT_PASSWORD", "")
REDDIT_USER_AGENT = "seo-inspector-bot/1.0 by Mehdi_Mouaffak"

SUBREDDITS = ["SEO", "webdev", "SideProject", "chrome_extensions", "indiehackers"]

POSTS = [
    {
        "subreddit": "SEO",
        "title": "I built a free Chrome extension that audits on-page SEO in one click",
        "body": "hey, been working on this for a bit and wanted to share. it checks the usual stuff like titles, meta descriptions, heading structure, image alts, links, https, mobile viewport. gives you a score out of 100 with breakdowns.\n\nthe backend is fastapi and the extension uses manifest v3. no signup needed for the free tier, just install and click analyze on whatever page you are on.\n\nwould love some honest feedback from people who actually do SEO for a living. what checks am i missing? what would make this actually useful for your workflow?\n\nlink: https://hernestagent.duckdns.org\nchrome store: search SEO Inspector"
    },
    {
        "subreddit": "webdev",
        "title": "Built a Chrome extension for on-page SEO audits, looking for feedback",
        "body": "spent the last few weeks building this as a side project. it is a chrome extension (manifest v3) with a fastapi backend that analyzes whatever page you are on and spits back an seo report.\n\ntech stack: python fastapi backend, sqlite, jwt auth, stripe for optional premium (5 bucks a month). the extension extracts the dom html and sends it to the api for parsing.\n\ni am a student so this is my first real project that is live. if any of you have experience with browser extensions or seo tools, i would really appreciate some feedback on the code or the product itself.\n\nhttps://hernestagent.duckdns.org"
    },
    {
        "subreddit": "SideProject",
        "title": "Weekend project that turned into two months, free SEO audit Chrome extension",
        "body": "started this as a weekend thing to learn how chrome extensions work and it spiraled. now it is a full chrome extension with a python backend that does on-page seo audits.\n\nfree tier lets you analyze any page. premium (5 chf/month) adds history and batch analysis.\n\nthis is my first time launching something publicly so if anyone has tips on getting those first users or feedback on the extension itself, i am all ears.\n\nhttps://hernestagent.duckdns.org"
    },
]


def post_to_reddit(subreddit, title, body):
    try:
        import praw
        reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            username=REDDIT_USERNAME,
            password=REDDIT_PASSWORD,
            user_agent=REDDIT_USER_AGENT,
        )
        sub = reddit.subreddit(subreddit)
        submission = sub.submit(title, selftext=body, send_replies=False)
        print(f"[{datetime.now()}] Posted to r/{subreddit}: {submission.url}")
        return submission.url
    except Exception as e:
        print(f"[{datetime.now()}] Failed r/{subreddit}: {e}")
        return None


def main():
    if not all([REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USERNAME, REDDIT_PASSWORD]):
        print("Missing Reddit credentials. Set REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USERNAME, REDDIT_PASSWORD")
        sys.exit(1)

    posted = json.load(open(os.path.expanduser("~/posted.json"))) if os.path.exists(os.path.expanduser("~/posted.json")) else {}

    for post in POSTS:
        key = f"{post[subreddit]}-{post[title][:30]}"
        if key in posted:
            continue
        url = post_to_reddit(post["subreddit"], post["title"], post["body"])
        if url:
            posted[key] = {"url": url, "date": str(datetime.now())}
            json.dump(posted, open(os.path.expanduser("~/posted.json"), "w"))
            time.sleep(60 + random.randint(30, 120))

    print(f"[{datetime.now()}] Done. Posted {len(posted)} total.")


if __name__ == "__main__":
    main()
