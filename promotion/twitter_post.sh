#!/bin/bash
export PATH=$HOME/.local/bin:$PATH
POSTS_FILE="$HOME/seo_posts.json"
POSTED_FILE="$HOME/seo_posted.json"

if [ ! -f "$POSTS_FILE" ]; then
    echo {posts: [{text: built a chrome extension that audits seo in one click. free, no signup needed. https://hernestagent.duckdns.org}, {text: it checks titles, meta descriptions, heading structure, image alts, links, mobile friendliness, https, and gives you an overall score out of 100.}, {text: tech stack: fastapi backend, sqlite, jwt auth, stripe for premium. i am a student at 42 lausanne and this is my first live project.}, {text: if you do seo or web dev, i would love some honest feedback. also on chrome web store, just search seo inspector.}]} > "$POSTS_FILE"
fi

for i in 0 1 2 3; do
    KEY="twitter-$i"
    if grep -q "$KEY" "$POSTED_FILE" 2>/dev/null; then
        continue
    fi
    TEXT=$(python3 -c "import json; print(json.load(open())[posts][$i][text])")
    echo "Posting tweet $i: ${TEXT:0:60}..."
    xurl post "$TEXT" 2>&1
    echo "$KEY $(date)" >> "$POSTED_FILE"
    sleep 300
done
echo "Twitter posting done"
