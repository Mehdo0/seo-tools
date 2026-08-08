# SEO Inspector — Launch Kit

Post these manually. Sound like a real person, not a bot.

---

## Reddit — r/SEO

**Title:** I built a free Chrome extension that audits on-page SEO in one click

**Body:**
hey, been working on this for a bit and wanted to share. it\s a chrome extension that checks the usual stuff — titles, meta descriptions, heading structure, image alts, links, https, mobile viewport. gives you a score out of 100 with breakdowns for each category.

the backend is fastapi and the extension uses manifest v3. no signup needed for the free tier, just install and click analyze on whatever page you\re on.

would love some honest feedback from people who actually do SEO for a living. what checks am i missing? what would make this actually useful for your workflow?

link: https://hernestagent.duckdns.org
chrome store: just search "SEO Inspector"

---

## Reddit — r/webdev

**Title:** Built a Chrome extension for on-page SEO audits — looking for feedback

**Body:**
spent the last few weeks building this as a side project. it\s a chrome extension (manifest v3) with a fastapi backend that analyzes whatever page you\re on and spits back an seo report.

tech stack: python fastapi backend on a vps, sqlite, jwt auth, stripe for optional premium (5 bucks a month, basically just to cover server costs). the extension extracts the html dom and sends it to the api for parsing.

i\m a student so this is my first real project that\s actually live. if any of you have experience with browser extensions or seo tools, i\d really appreciate some feedback on the code or the product itself.

https://hernestagent.duckdns.org

---

## Reddit — r/SideProject

**Title:** Weekend project that turned into two months — free SEO audit Chrome extension

**Body:**
started this as a weekend thing to learn how chrome extensions work and it kinda spiraled. now it\s a full chrome extension with a python backend that does on-page seo audits.

free tier lets you analyze any page. premium (5 chf/month) adds history and some extra scraping features but honestly the free version does 90% of what most people need.

this is my first time launching something publicly so if anyone has tips on getting those first users or feedback on the extension itself, i\m all ears.

https://hernestagent.duckdns.org

---

## Product Hunt — Draft

**Tagline:** One-click on-page SEO audit for any website

**Description:**
I built SEO Inspector because I was tired of copying HTML into online SEO checkers. It\s a Chrome extension that analyzes the page you\re currently viewing — titles, meta tags, headings, images, links, mobile friendliness, HTTPS — and gives you a score with specific fixes.

Free tier, no account needed. Premium adds audit history and batch analysis.

Built with Python (FastAPI), SQLite, and Chrome Manifest V3. Stripe for payments.

Looking for feedback from SEO folks, web developers, and anyone who cares about their site\s search ranking.

**Maker comment (first comment after launch):**
hey everyone, mehdi here. i\m a 42 lausanne student and this is my first real product launch. the extension came out of frustration with existing tools being either too expensive or too complicated for quick checks.

would love to hear what you think — what features would make this a daily tool for you? happy to answer questions about the tech stack or the build process.

---

## Twitter/X — Thread

**Post 1:**
built a chrome extension that audits seo in one click. free, no signup needed.

**Post 2:**
it checks titles, meta descriptions, heading structure, image alts, links, mobile friendliness, https, and gives you an overall score.

**Post 3:**
tech stack: fastapi backend on a vps, sqlite for persistence, jwt auth, stripe for premium (5 chf/month).

**Post 4:**
im a student at 42 lausanne and this is my first live project. if you do seo or web dev, id love some honest feedback.

**Post 5:**
link in bio. also on chrome web store — just search seo inspector.

---

## Setup X/Twitter

Run these manually on VM Manager:

```bash
# 1. Create app at https://developer.x.com/en/portal/dashboard
# 2. Set redirect URI to http://localhost:8080/callback
# 3. Register app
export PATH=$HOME/.local/bin:$PATH
xurl auth apps add seo-inspector --client-id YOUR_CLIENT_ID --client-secret YOUR_CLIENT_SECRET
xurl auth oauth2 --app seo-inspector YOUR_USERNAME
xurl auth default seo-inspector YOUR_USERNAME

# 4. Post the thread
xurl post "Post 1 text here"
```
