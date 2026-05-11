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
