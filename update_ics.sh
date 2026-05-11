#!/bin/bash

# Go to the folder where this script is located
cd "$(dirname "$0")"

# Load environment variables from .env if present
if [ -f .env ]; then
    set -o allexport
    source .env
    set +o allexport
fi

# Run the Python script that updates the ICS file
python3 past_feed_to_ics.py

# Commit and push the updated ICS to GitHub so the calendar feed is live
git pull --rebase origin main
git add past_feed.ics
git diff --cached --quiet && echo "No changes to ICS, skipping commit." && exit 0
git commit -m "Update ICS feed $(date -u +"%Y%m%dT%H%M%SZ")"
git push origin main
