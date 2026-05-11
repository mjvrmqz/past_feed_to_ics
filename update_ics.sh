#!/bin/bash

cd "$(dirname "$0")"

if [ -f .env ]; then
    set -o allexport
    source .env
    set +o allexport
fi

python3 past_feed_to_ics.py

git remote set-url origin https://github.com/mjvrmqz/Past-Feed.git
git stash
git fetch origin
git rebase origin/main
git stash pop
git add "Past Feed.ics"
git diff --cached --quiet && echo "No changes to ICS, skipping commit." && exit 0
git commit -m "Update ICS feed $(date -u +"%Y%m%dT%H%M%SZ")"
git push origin main
